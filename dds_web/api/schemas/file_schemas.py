"""File related marshmallow schemas."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
from datetime import datetime
import os

# Installed
import marshmallow
import sqlalchemy
import flask

# Own modules
from dds_web.database import models
import dds_web.utils
from dds_web.api.schemas import project_schemas
from dds_web import ma
from dds_web.api import api_s3_connector
from dds_web.api.schemas import sqlalchemyautoschemas

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


class FileInfoSchema(project_schemas.ProjectRequiredSchema):
    """Schema for project contents."""

    contents = marshmallow.fields.List(marshmallow.fields.String)
    url = marshmallow.fields.Boolean(required=False, default=False)

    @marshmallow.post_dump
    def return_items(self, data, **kwargs):
        contents = data.get("contents")
        project_row = project_schemas.verify_project_exists(spec_proj=data.get("project"))

        # Tools for getting file information
        url = data.get("url")  # Get url for file?
        fileschema = sqlalchemyautoschemas.FileSchema(
            many=False,
            only=(
                "name_in_bucket",
                "subpath",
                "size_original",
                "size_stored",
                "salt",
                "public_key",
                "checksum",
                "compressed",
            ),
        )

        # Found items
        found_files = {}
        found_folder_contents = {}

        # Check if in bucket
        with api_s3_connector.ApiS3Connector(project=project_row) as s3:

            # If single file, check head bucket
            # TODO

            # If more files then paginate
            pages = s3.bucket_items()

            # Iterate through pages and search for files
            for page in pages:
                flask.current_app.logger.debug(f"Page contents: {page}")
                found_files.update(
                    {
                        x.name: {
                            **fileschema.dump(x),
                            "url": s3.generate_get_url(key=x.name_in_bucket) if url else None,
                        }
                        for x in files
                        if x.name_in_bucket in page
                    }
                )
                flask.current_app.logger.debug(f"found files: {found_files}")

                for x, y in folder_contents.items():
                    if x not in found_folder_contents:
                        found_folder_contents[x] = {}

                    found_folder_contents[x].update(
                        {
                            z.name: {
                                **fileschema.dump(z),
                                "url": s3.generate_get_url(key=z.name_in_bucket) if url else None,
                            }
                            for z in y
                            if z.name_in_bucket in page
                        }
                    )
                    flask.current_app.logger.debug(
                        f"Found folder contents: {found_folder_contents}"
                    )

        return found_files, found_folder_contents, not_found
