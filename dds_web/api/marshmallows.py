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
from dds_web.api import db_connector

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

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def get_project_object(self, data, **kwargs):
        """Set project row in data for access by validators."""

        data["project_row"] = verify_project_exists(spec_proj=data.get("project"))

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Return project object."""

        return data.get("project_row")


class PublicKeySchema(ProjectRequiredSchema):
    """Schema for returning the public key."""

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Get and return public key."""

        public_key = data.get("project_row").public_key
        if not public_key:
            raise ddserr.PublicKeyNotFoundError(project=data.get("project"))

        return public_key


class PrivateKeySchema(ProjectRequiredSchema):
    """Schema for returning the private key along with nonce and salt."""

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Get and return project private key, nonce and salt."""

        project_info = data.get("project_row")

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
        project = data.get("project_row")
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


class MatchFilesSchema(ProjectRequiredSchema):
    """Finds files in database matching requested."""

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Return the required file information."""

        project = data.get("project_row")
        try:
            files = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.name.in_(flask.request.json),
                    models.File.project_id == sqlalchemy.func.binary(project.id),
                )
            ).all()
        except sqlalchemy.exc.SQLAlchemyError:
            raise

        return files


class FileSchema(ProjectRequiredSchema):
    """Returns information on all files in project."""

    subpath = marshmallow.fields.Boolean(required=False, default=None)

    class Meta:
        unknown = marshmallow.EXCLUDE

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def format_subpath(self, data, **kwargs):
        """Format subpath."""

        subpath = data.get("subpath")
        data["subpath"] = subpath.rstrip(os.sep) if subpath else "."

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def verify_files_in_project(self, data, **kwargs):
        """Checks that the project contains files."""

        project = data.get("project_row")
        num_files_in_project = utils.project_size_num(project=project)

        if not num_files_in_project:
            raise ddserr.EmptyProjectException(project=data.get("project"))

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Return files from database."""

        try:
            distinct_files, distinct_folders = utils.items_in_subpath(
                project=data.get("project_row"), folder=data.get("subpath")
            )
        except ddserr.DatabaseError:
            raise

        return distinct_files, distinct_folders


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

        project = data.get("project_row")
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

        project = data.get("project_row")
        # Update foreign keys
        project.file_versions.append(new_version)
        project.files.append(new_file)
        new_file.versions.append(new_version)

        return new_file


class NewVersionSchema(ProjectRequiredSchema):
    """Checks that a user has permissions to update file info."""

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
    def verify_exists(self, data, **kwargs):
        """Verify that the file exists -- cannot update non existent file."""

        project = data.get("project_row")
        try:
            existing_file = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.name == sqlalchemy.func.binary(data.get("name")),
                    models.File.project_id == project.id,
                )
            ).first()

            if not existing_file:
                raise FileNotFoundError

            current_file_version = models.Version.query.filter(
                sqlalchemy.and_(
                    models.Version.active_file == sqlalchemy.func.binary(existing_file.id),
                    models.Version.time_deleted == None,
                )
            ).all()

            if len(current_file_version) > 1:
                flask.current_app.logger.warning(
                    "There is more than one version of the file which does not yet have a deletion timestamp."
                )

        except (sqlalchemy.exc.SQLAlchemyError, FileNotFoundError):
            raise
        else:
            data.update(
                {
                    "file": existing_file,
                    "version": current_file_version[0],
                }
            )

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Update file info."""

        # Same timestamp for deleted and created new file
        new_timestamp = utils.current_time()

        # Overwritten == deleted / deactivated
        old_version = data.get("version")
        old_version.time_deleted = new_timestamp

        # Update file info
        file = data.get("file")
        file.subpath = data.get("subpath")
        file.size_original = data.get("size")
        file.size_stored = data.get("size_processed")
        file.compressed = data.get("compressed")
        file.salt = data.get("salt")
        file.public_key = data.get("public_key")
        file.time_uploaded = new_timestamp
        file.checksum = data.get("checksum")

        # New version
        new_version = models.Version(
            size_stored=data.get("size_processed"),
            time_uploaded=new_timestamp,
        )

        project = data.get("project_row")
        # Update foreign keys and relationships
        project.file_versions.append(new_version)
        file.versions.append(new_version)

        return new_version
