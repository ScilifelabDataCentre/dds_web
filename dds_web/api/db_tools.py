"""Tools for database queries."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library

# Installed
import sqlalchemy

# Own modules
from dds_web.database import models
from dds_web import db
from dds_web.errors import (
    DatabaseError,
    UserDeletionError,
    DDSArgumentError,
    NoSuchProjectError,
    AccessDeniedError,
)
from dds_web import auth

####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def remove_user_self_deletion_request(user: models.User):
    """Remove a row in the DeletionRequest table."""
    if not user:
        raise UserDeletionError(message="User object needed to get deletion request.")

    try:
        request_row = models.DeletionRequest.query.filter(
            models.DeletionRequest.requester_id == user.username
        ).one_or_none()
        if not request_row:
            raise UserDeletionError("There is no deletion request from this user.")

        email = request_row.email
        db.session.delete(request_row)
        db.session.commit()
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError) as err:
        db.session.rollback()
        raise DatabaseError(
            message=str(err),
            alt_message=(
                "Failed to remove deletion request"
                + (
                    ": Database malfunction."
                    if isinstance(err, sqlalchemy.exc.OperationalError)
                    else "."
                )
            ),
        ) from err

    return email


def get_project_object(public_id: str) -> models.Project:
    """Get project object from specified public id."""
    if not public_id:
        raise DDSArgumentError(message="Project ID required.")

    # Get project and verify that it exists
    project = models.Project.query.filter(
        models.Project.public_id == sqlalchemy.func.binary(public_id)
    ).one_or_none()
    if not project:
        raise NoSuchProjectError(project=public_id)

    # Verify project access
    if not auth.current_user():
        raise AccessDeniedError(message="No authenticated user. Project access denied.")
    if project not in auth.current_user().projects:
        raise AccessDeniedError(
            message="Project access denied.",
            username=auth.current_user().username,
            project=project.public_id,
        )

    # Return row
    return project
