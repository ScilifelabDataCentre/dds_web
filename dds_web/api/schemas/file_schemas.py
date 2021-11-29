"""File related marshmallow schemas."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
from datetime import datetime

# Installed
import marshmallow
import sqlalchemy
import flask

# Own modules
from dds_web.database import models
import dds_web.utils
from dds_web.api.schemas import project_schemas
from dds_web import ma

####################################################################################################
# SCHEMAS ################################################################################ SCHEMAS #
####################################################################################################


class NewFileSchema(project_schemas.ProjectRequiredSchema):
    """Validates and creates a new file object."""

    # Length minimum 1 required, required=True accepts empty string
    name = marshmallow.fields.String(required=True, validate=marshmallow.validate.Length(min=1))
    name_in_bucket = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(min=1)
    )
    subpath = marshmallow.fields.String(required=True, validate=marshmallow.validate.Length(min=1))
    size = marshmallow.fields.Integer(required=True)  # Accepts BigInt
    size_processed = marshmallow.fields.Integer(required=True)  # Accepts BigInt
    compressed = marshmallow.fields.Boolean(required=True)  # Accepts all truthy
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

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Create file object."""

        new_file = models.File(
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
            size_stored=new_file.size_stored, time_uploaded=dds_web.utils.current_time()
        )

        project = data.get("project_row")
        # Update foreign keys
        project.file_versions.append(new_version)
        project.files.append(new_file)
        new_file.versions.append(new_version)

        return new_file


class FileSchema(ma.SQLAlchemyAutoSchema):
    """ """

    class Meta:
        model = models.File

    @marshmallow.post_dump
    def return_dicts(self, data, many, **kwargs):
        """ """

        flask.current_app.logger.debug(f"Input data: {data}")
        name = data.pop("name")
        return {name: data}


class FileInfoSchema(project_schemas.ProjectRequiredSchema):
    """Schema for project contents."""

    contents = marshmallow.fields.List(marshmallow.fields.String)
    url = marshmallow.fields.Boolean()

    # @marshmallow.validates_schema(skip_on_field_errors=True)
    # def check_for_existing(self, data, **kwargs):

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Return files and folders"""

        flask.current_app.logger.info(f"Validating contents: {data}")

        contents = data.get("contents")
        project = data.get("project_row")
        print(project, flush=True)

        # All contents (query only, not run)
        all_contents_query = models.File.query.filter(
            models.File.project_id == sqlalchemy.func.binary(project.id)
        )

        # Get all files
        files = all_contents_query.filter(models.File.name.in_(contents)).all()
        flask.current_app.logger.debug(f"Files: {files}")

        # Get not found paths - may be folders
        new_paths = set(contents).difference(x.name for x in files)
        flask.current_app.logger.debug(f"New paths: {new_paths}")

        # Get all folder contents
        folder_contents = {
            x: all_contents_query.filter(models.File.subpath.like(f"{x.rstrip(os.sep)}%")).all()
            for x in new_paths
        }
        flask.current_app.logger.debug(f"Folder contents: {folder_contents}")

        # Not found
        not_found = {x: folder_contents.pop(x) for x, y in list(folder_contents.items()) if not y}
        flask.current_app.logger.debug(f"Not found: {not_found}")

        url = data.get("url")

        # Which columns to fetch from database
        common_columns = (
            "name",
            "name_in_bucket",
            "subpath",
            "size_original",
            "size_stored",
            "salt",
            "public_key",
            "checksum",
            "compressed",
        )
        fileschema = file_schemas.FileSchema(many=True, only=common_columns)

        # Check if in bucket
        with api_s3_connector.ApiS3Connector(project=project) as s3:
            flask.current_app.logger.debug([x.name_in_bucket for x in files])

            # TODO: Att check for if only one file and then just get that object

            # Generator for returning project bucket items
            pages = s3.bucket_items()
            found_files = []
            found_folder_contents = {}

            # Iterate through pages and search for files
            for page in pages:
                flask.current_app.logger.debug(f"page contents: {page}")
                found_files += [
                    fileschema.dump(x).update({"url": "test" if url else None})
                    for x in files
                    if x.name_in_bucket in page
                ]

                flask.current_app.logger.debug(f"found files: {found_files}")
                for x, y in folder_contents.items():
                    found_folder_contents[x] = [z for z in y if z.name_in_bucket in page]
                    flask.current_app.logger.debug(
                        f"found folder contents: {found_folder_contents}"
                    )

        return
        return project, files, folder_contents, not_found

    @marshmallow.post_dump
    def return_items(self, data, many, **kwargs):
        return
