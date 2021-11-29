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

# Own modules
from dds_web.api import errors as ddserr
from dds_web import auth
from dds_web.database import models
from dds_web import ma
from dds_web.api import api_s3_connector

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

        flask.current_app.logger.debug(f"project: {value}")
        project = verify_project_exists(spec_proj=value)
        verify_project_access(project=project)

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def get_project_object(self, data, **kwargs):
        """Set project row in data for access by validators."""

        data["project_row"] = verify_project_exists(spec_proj=data.get("project"))
        flask.current_app.logger.debug(f"project row: {data.get('project_row')}")

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Return project object."""

        return data.get("project_row")
