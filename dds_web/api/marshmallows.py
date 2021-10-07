####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library

# Installed
import flask
import marshmallow
import sqlalchemy

# Own modules
from dds_web import utils
from dds_web.api import errors as ddserr
from dds_web import auth
from dds_web import ROLES
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
        raise marshmallow.ValidationError("Invalid project.")

    return project


def verify_project_access(project):
    """Check users access to project."""

    if project not in auth.current_user().projects:
        raise marshmallow.ValidationError("Project access denied.")

    return project


def verify_method_access(spec_meth):
    """Check that user has permission to perform method"""

    if spec_meth not in ROLES[auth.current_user().role]:
        raise marshmallow.ValidationError(
            f"User does not have the neccessary permissions to perform this action: {spec_meth}"
        )


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


class PublicKeySchema(ProjectRequiredSchema):
    """Schema for verifying the methods access to the public key and returning the key."""

    method = marshmallow.fields.String(
        required=True,
        validate=[marshmallow.validate.OneOf(choices=["put", "get"]), verify_method_access],
    )

    @marshmallow.post_load
    def return_key(self, data, **kwargs):
        """Get and return public key."""

        public_key = verify_project_exists(spec_proj=data.get("project")).public_key
        if not public_key:
            raise ddserr.PublicKeyNotFoundError(project=data.get("project"))

        return public_key


class PrivateKeySchema(marshmallow.Schema):
    """Schema for verifying the methods access to the private key and
    returning the key along with nonce and salt."""

    method = marshmallow.fields.String(
        required=True,
        validate=[marshmallow.validate.OneOf(choices=["get"]), verify_method_access],
    )

    @marshmallow.post_load
    def return_key(self, data, **kwargs):
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
