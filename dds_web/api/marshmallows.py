####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import pathlib
import json
import os

# Installed
import flask
import marshmallow
import sqlalchemy

# Own modules
from dds_web import utils
from dds_web.api import errors as ddserr
from dds_web import auth
from dds_web.database import models

####################################################################################################
# VALIDATORS ########################################################################## VALIDATORS #
####################################################################################################


def verify_project_exists(spec_proj):
    """Check that project exists."""

    try:
        project = models.Project.query.filter(
            models.Project.public_id == sqlalchemy.func.binary(spec_proj)
        ).one_or_none()
    except sqlalchemy.exc.SQLAlchemyError as sqlerr:
        raise

    if not project:
        flask.current_app.logger.warning("No such project!!")
        raise ddserr.NoSuchProjectError

    return project


def verify_project_access(project):
    """Check users access to project."""

    if project not in auth.current_user().projects:
        raise ddserr.AccessDeniedError(
            message="Project access denied.",
            username=auth.current_user().username,
            project=project.public_id,
        )

    return project


####################################################################################################
# SCHEMAS ################################################################################ SCHEMAS #
####################################################################################################


class ProjectRequiredSchema(marshmallow.Schema):
    """Schema for verifying an existing project in args and database."""

    project = marshmallow.fields.String(required=True)

    class Meta:
        unknown = marshmallow.RAISE

    @marshmallow.validates("project")
    def validate_project(self, value):
        """Validate existing project and user access to it."""

        project = verify_project_exists(spec_proj=value)
        verify_project_access(project=project)

    @marshmallow.post_load
    def return_items(self, data, **kwargs):

        return verify_project_exists(spec_proj=data.get("project"))


class UpdatePermissionsRequiredSchema(UploadPermissionsRequiredSchema):
    """TEMPORARY, WILL BE MERGED WITH UPLOADPERMISSIONS LATER.
    Checks that a user has permissions to update file info."""

    class Meta:
        unknown = marshmallow.EXCLUDE


class DeletePermissionsRequiredSchema(ProjectRequiredSchema):
    """Schema for verifying the current users permissions to delete."""

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def validate_put_access(self, data, **kwargs):
        """Verify that the user has access to delete data."""

        if auth.current_user().role not in ["Super Admin", "Unit Admin", "Unit Personnel"]:
            raise ddserr.AccessDeniedError(
                message="User does not have upload permissions.",
                username=auth.current_user().username,
                project=data.get("project"),
            )


class PublicKeySchema(ProjectRequiredSchema):
    """Schema for returning the public key."""

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Get and return public key."""

        public_key = verify_project_exists(spec_proj=data.get("project")).public_key
        if not public_key:
            raise ddserr.PublicKeyNotFoundError(project=data.get("project"))

        return public_key


class PrivateKeySchema(ProjectRequiredSchema):
    """Schema for returning the private key along with nonce and salt."""

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Get and return project private key, nonce and salt."""

        project_info = verify_project_exists(spec_proj=data.get("project"))

        if not all(
            [project_info.private_key, project_info.privkey_nonce, project_info.privkey_salt]
        ):
            raise ddserr.PrivateKeyNotFoundError(project=data.get("project"))

        return (
            bytes.fromhex(x)
            for x in [
                project_info.private_key,
                project_info.privkey_nonce,
                project_info.privkey_salt,
            ]
        )


class S3KeySchema(ProjectRequiredSchema):
    """Validate and get S3 keys."""

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Get key"""

        # Get safespring project name
        project = verify_project_exists(spec_proj=data.get("project"))
        safespring_project = project.safespring_project
        if not safespring_project:
            raise ddserr.S3ProjectNotFoundError

        # Get path to key file
        s3_keys_path_string = flask.current_app.config.get("DDS_S3_CONFIG")
        if not s3_keys_path_string:
            raise ddserr.S3InfoNotFoundError(message="API failed getting the s3 config file path.")

        # Get safespring project keys
        s3_keys_path = pathlib.Path(s3_keys_path_string)
        if not s3_keys_path.exists():
            raise FileNotFoundError("DDS S3 config file not found.")
        try:
            with s3_keys_path.open(mode="r") as f:
                s3_keys = json.load(f).get("sfsp_keys").get(safespring_project)

            with s3_keys_path.open(mode="r") as f:
                endpoint_url = json.load(f).get("endpoint_url")

            if not all([s3_keys.get("access_key"), s3_keys.get("secret_key")]):
                raise ddserr.S3KeysNotFoundError(
                    project=self.project,
                    message="Safespring S3 access or secret key not found in s3 config file.",
                )
        except ddserr.S3KeysNotFoundError:
            raise

        return project, safespring_project, endpoint_url, s3_keys


class ExistingFilesSchema(UploadPermissionsRequiredSchema):
    """Finds files in database matching requested."""

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Return the required file information."""

        try:
            files = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.name.in_(flask.request.json),
                    models.File.project_id == sqlalchemy.func.binary(data.get("project")),
                )
            ).all()
        except sqlalchemy.exc.SQLAlchemyError:
            raise

        return files


class NewFileSchema(ProjectRequiredSchema):
    """Validates and creates a new file object."""

    name = marshmallow.fields.String(required=True, validate=marshmallow.validate.Length(min=1))
    name_in_bucket = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(min=1)
    )
    subpath = marshmallow.fields.String(required=True, validate=marshmallow.validate.Length(min=1))
    size = marshmallow.fields.Integer(required=True)  # TODO: check that this accepts BIGINT
    size_processed = marshmallow.fields.Integer(required=True)
    compressed = marshmallow.fields.Boolean(required=True)
    public_key = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(equal=64)
    )
    salt = marshmallow.fields.String(required=True, validate=marshmallow.validate.Length(equal=32))
    checksum = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(equal=64)
    )

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def verify_file_not_exists(self, data, **kwargs):
        """Check that the file does not match anything already in the database."""

        # Generate new public file id and check that there isn't one in the database
        public_id = os.urandom(16).hex()
        try:
            public_id_in_db = models.File.query.filter_by(public_id=public_id).one_or_none()
        except sqlalchemy.exc.SQLAlchemyError:
            raise
        if public_id_in_db:
            raise FileExistsError
        data["public_id"] = public_id

        # Check that there is no such file in the database

        project = verify_project_exists(spec_proj=data.get("project"))
        try:
            file = (
                models.File.query.filter(
                    sqlalchemy.and_(
                        models.File.name == sqlalchemy.func.binary(data.get("name")),
                        models.File.project_id == sqlalchemy.func.binary(project.id),
                    )
                )
                .with_entities(models.File.id)
                .one_or_none()
            )
        except sqlalchemy.exc.SQLAlchemyError:
            raise

        if file:
            raise FileExistsError

        data["project"] = project

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Create file object."""

        new_file = models.File(
            public_id=data.get("public_id"),
            name=data.get("name"),
            name_in_bucket=data.get("name_in_bucket"),
            subpath=data.get("subpath"),
            size_original=data.get("size"),
            size_stored=data.get("size_processed"),
            compressed=data.get("compressed"),
            salt=data.get("salt"),
            public_key=data.get("public_key"),
            checksum=data.get("checksum"),
        )

        new_version = models.Version(
            size_stored=new_file.size_stored, time_uploaded=utils.current_time()
        )

        return new_file, new_version, data.get("project")


class FileInfoSchema(ProjectRequiredSchema):
    """Returns file info."""


class UpdateDownloadTimeSchema(ProjectRequiredSchema):
    """Updates a files download time."""

    class Meta:
        unknown = marshmallow.EXCLUDE
