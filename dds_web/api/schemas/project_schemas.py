"""Project related marshmallow schemas."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
from datetime import datetime
import os

# Installed
import flask
import marshmallow
import sqlalchemy

# Own modules
from dds_web.api import errors as ddserr
from dds_web import auth
from dds_web.database import models
from dds_web.api import api_s3_connector
from dds_web.api.schemas import sqlalchemyautoschemas

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
        raise ddserr.NoSuchProjectError(project=spec_proj)

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
        unknown = marshmallow.EXCLUDE  # TODO: Change to RAISE

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


class ProjectContentSchema(ProjectRequiredSchema):
    """ """

    requested_items = marshmallow.fields.List(marshmallow.fields.String, required=False)
    url = marshmallow.fields.Boolean(required=False, default=False)
    get_all = marshmallow.fields.Boolean(required=False, default=False)

    def find_contents(self, project, contents):

        # All contents
        all_contents_query = models.File.query.filter(
            models.File.project_id == sqlalchemy.func.binary(project.id)
        )

        # Get all files
        files = all_contents_query.filter(models.File.name.in_(contents)).all()

        # Get not found paths - may be folders
        new_paths = set(contents).difference(x.name for x in files)

        # Get all folder contents
        folder_contents = {
            x: all_contents_query.filter(models.File.subpath.like(f"{x.rstrip(os.sep)}%")).all()
            for x in new_paths
        }

        # Not found
        not_found = {x: folder_contents.pop(x) for x, y in list(folder_contents.items()) if not y}

        return files, folder_contents, not_found

    @marshmallow.post_dump
    def return_items(self, data, **kwargs):
        """Return project contents as serialized."""

        # Fields
        requested_items = data.get("requested_items")
        url = data.get("url")
        get_all = data.get("get_all")

        # Check if project has contents
        project_row = verify_project_exists(spec_proj=data.get("project"))
        if not project_row.files:
            raise ddserr.EmptyProjectException

        # Check if specific files have been requested or if requested all contents
        files, folder_contents, not_found = (None, None, None)
        if requested_items:
            files, folder_contents, not_found = self.find_contents(
                project=project_row, contents=requested_items
            )
        elif get_all:
            files = project_row.files
        else:
            raise ddserr.DDSArgumentError(message="No items were requested.")

        # Items to return
        found_files = {}
        found_folder_contents = {}
        not_found = {}

        # Use file schema to get file info automatically
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

        # Connect to s3
        with api_s3_connector.ApiS3Connector(project=project_row) as s3:
            # TODO: Optimisation: Add check for if only searching for one file (head_bucket)
            # Get bucket items
            pages = s3.bucket_items()

            # Get the info and signed urls for all files found in the bucket
            for page in pages:
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

                if folder_contents:
                    # Get all info and signed urls for all folder contents found in the bucket
                    for x, y in folder_contents.items():
                        if x not in found_folder_contents:
                            found_folder_contents[x] = {}

                        found_folder_contents[x].update(
                            {
                                z.name: {
                                    **fileschema.dump(z),
                                    "url": s3.generate_get_url(key=z.name_in_bucket)
                                    if url
                                    else None,
                                }
                                for z in y
                                if z.name_in_bucket in page
                            }
                        )

        return found_files, found_folder_contents, not_found
