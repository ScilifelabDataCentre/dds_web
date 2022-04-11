"""Project related marshmallow schemas."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import os
import re

# Installed
import botocore.client
import flask
import marshmallow
import sqlalchemy

# Own modules
from dds_web import errors as ddserr
from dds_web import auth
from dds_web.database import models
from dds_web.api import api_s3_connector
from dds_web.api.schemas import sqlalchemyautoschemas
from dds_web.api.schemas import custom_fields
from dds_web.security.project_user_keys import generate_project_key_pair
import dds_web.utils

####################################################################################################
# VALIDATORS ########################################################################## VALIDATORS #
####################################################################################################


def verify_project_exists(spec_proj):
    """Check that project exists."""

    project = models.Project.query.filter(
        models.Project.public_id == sqlalchemy.func.binary(spec_proj)
    ).one_or_none()

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
class CreateProjectSchema(marshmallow.Schema):
    """Schema for creating a project."""

    class Meta:
        unknown = marshmallow.EXCLUDE

    title = marshmallow.fields.String(
        required=True,
        allow_none=False,
        validate=marshmallow.validate.And(
            marshmallow.validate.Length(min=1), dds_web.utils.contains_disallowed_characters
        ),
        error_messages={
            "required": {"message": "Title is required."},
            "null": {"message": "Title is required."},
        },
    )
    description = marshmallow.fields.String(
        required=True,
        allow_none=False,
        validate=marshmallow.validate.Length(min=1),
        error_messages={
            "required": {"message": "A project description is required."},
            "null": {"message": "A project description is required."},
        },
    )
    pi = marshmallow.fields.String(
        required=True,
        allow_none=False,
        validate=marshmallow.validate.Email(error="The PI email is invalid."),
        error_messages={
            "required": {"message": "A principal investigator is required."},
            "null": {"message": "A principal investigator is required."},
        },
    )
    non_sensitive = marshmallow.fields.Boolean(required=False, default=False)
    date_created = custom_fields.MyDateTimeField(required=False)

    @marshmallow.pre_load
    def generate_required_fields(self, data, **kwargs):
        """Generate all required fields for creating a project."""
        if not data:
            raise ddserr.DDSArgumentError(
                "No project information found when attempting to create project."
            )

        data["date_created"] = dds_web.utils.current_time()

        return data

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def validate_all_fields(self, data, **kwargs):
        """Validate that all fields are present."""
        if not all(
            field in data
            for field in [
                "title",
                "date_created",
                "description",
                "pi",
            ]
        ):
            raise marshmallow.ValidationError("Missing fields!")

    @marshmallow.validates("description")
    def validate_description(self, value):
        """Verify that description only has words, spaces and . / ,."""
        disallowed = re.findall(r"[^(\w\s.,)]+", value)
        if disallowed:
            raise marshmallow.ValidationError(
                message="The description can only contain letters, spaces, period and commas."
            )

    def generate_bucketname(self, public_id, created_time):
        """Create bucket name for the given project."""
        return "{pid}-{tstamp}-{rstring}".format(
            pid=public_id.lower(),
            tstamp=dds_web.utils.timestamp(dts=created_time, ts_format="%y%m%d%H%M%S%f"),
            rstring=os.urandom(4).hex(),
        )

    @marshmallow.post_load
    def create_project(self, data, **kwargs):
        """Create project row in db."""

        # Lock db, get unit row and update counter
        unit_row = (
            models.Unit.query.filter_by(id=auth.current_user().unit_id)
            .with_for_update()
            .one_or_none()
        )
        if not unit_row:
            raise ddserr.AccessDeniedError(message="Error: Your user is not associated to a unit.")

        unit_row.counter = unit_row.counter + 1 if unit_row.counter else 1
        data["public_id"] = "{}{:05d}".format(unit_row.internal_ref, unit_row.counter)

        # Generate bucket name
        data["bucket"] = self.generate_bucketname(
            public_id=data["public_id"], created_time=data["date_created"]
        )

        # Create project
        current_user = auth.current_user()
        new_project = models.Project(
            **{**data, "unit_id": current_user.unit.id, "created_by": current_user.username}
        )
        new_project.project_statuses.append(
            models.ProjectStatuses(
                **{
                    "status": "In Progress",
                    "date_created": data["date_created"],
                }
            )
        )
        generate_project_key_pair(current_user, new_project)

        return new_project


class ProjectRequiredSchema(marshmallow.Schema):
    """Schema for verifying an existing project in args and database."""

    project = marshmallow.fields.String(
        required=True,
        allow_none=False,
        error_messages={
            "required": {"message": "Project ID required."},
            "null": {"message": "Project ID cannot be null."},
        },
    )

    class Meta:
        unknown = marshmallow.EXCLUDE

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
            raise ddserr.EmptyProjectException(project=project_row.public_id)

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
            # Get the info and signed urls for all files
            try:
                found_files.update(
                    {
                        x.name: {
                            **fileschema.dump(x),
                            "url": s3.generate_get_url(key=x.name_in_bucket) if url else None,
                        }
                        for x in files
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
                            }
                        )
            except botocore.client.ClientError as clierr:
                raise ddserr.S3ConnectionError(
                    message=str(clierr), alt_message="Could not generate presigned urls."
                )

        return found_files, found_folder_contents, not_found
