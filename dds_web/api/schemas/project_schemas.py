"""Project related marshmallow schemas."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
from datetime import datetime
import os
import gc

# Installed
import flask
import marshmallow
import sqlalchemy
import botocore

# Own modules
from dds_web.api import errors as ddserr
from dds_web import auth
from dds_web.database import models
from dds_web import ma
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
        flask.current_app.logger.debug(f"Files: {files}")

        # Get not found paths - may be folders
        new_paths = set(contents).difference(x.name for x in files)
        flask.current_app.logger.debug(f"Not found yet: {new_paths}")

        # Get all folder contents
        folder_contents = {
            x: all_contents_query.filter(models.File.subpath.like(f"{x.rstrip(os.sep)}%")).all()
            for x in new_paths
        }
        flask.current_app.logger.debug(f"Folder contents: {folder_contents}")

        # Not found
        not_found = {x: folder_contents.pop(x) for x, y in list(folder_contents.items()) if not y}
        flask.current_app.logger.debug(f"Not found: {not_found}")

        return files, folder_contents, not_found

    @marshmallow.post_dump
    def return_items(self, data, **kwargs):
        """ """

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
            flask.current_app.logger.debug(
                f"\n\nFiles: {files}\n\nFolders: {folder_contents}\n\nNot found: {not_found}\n\n"
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

        with api_s3_connector.ApiS3Connector(project=project_row) as s3:

            flask.current_app.logger.debug(f"Length of files: {len(files)}")
            flask.current_app.logger.debug(f"Length of folders: {len(folder_contents)}")
            if len(files) > 1 or len(folder_contents) > 1:
                flask.current_app.logger.debug("Longer than 1.")
                pages = s3.bucket_items()
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
                            flask.current_app.logger.debug(
                                f"Found folder contents: {found_folder_contents}"
                            )
            else:
                flask.current_app.logger.debug("Less than 1.")
                if len(files) == 1:
                    (only_file,) = files
                    if s3.key_in_bucket(key=only_file.name_in_bucket):
                        found_files[only_file.name] = {
                            **fileschema.dump(only_file),
                            "url": s3.generate_get_url(key=only_file.name_in_bucket)
                            if url
                            else None,
                        }

                if len(folder_contents) == 1:
                    only_folder = next(iter(folder_contents))
                    if len(folder_contents[only_folder]) == 1:
                        (only_file,) = folder_contents[only_folder]
                        found_folder_contents[only_folder] = {
                            only_file.name: {
                                **fileschema.dump(only_file),
                                "url": s3.generate_get_url(key=only_file.name_in_bucket)
                                if url
                                else None,
                            }
                        }

        [found_folder_contents.pop(x) for x, y in found_folder_contents.items() if not y]
        return found_files, found_folder_contents, not_found
