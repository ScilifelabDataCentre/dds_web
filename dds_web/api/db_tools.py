"""Tools for database queries."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library

# Installed
import sqlalchemy
import flask 

# Own modules
from dds_web.database import models
from dds_web import db
from dds_web.errors import (
    DatabaseError,
    UserDeletionError,
    DDSArgumentError,
    NoSuchProjectError
)

####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def remove_user_self_deletion_request(user):

    try:
        request_row = models.DeletionRequest.query.filter(
            models.DeletionRequest.requester_id == user.username
        ).with_for_update().one_or_none()
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

def get_project_object(project_id, for_update=False):
    """Check if project exists and return the database row."""
    if not project_id:
        raise DDSArgumentError(message="Project ID required.")
    project_query = models.Project.query.filter(
        models.Project.public_id == sqlalchemy.func.binary(project_id)
    )
    project = project_query.with_for_update().one_or_none() if for_update else project_query.one_or_none()

    if not project:
        flask.current_app.logger.warning("No such project!!")
        raise NoSuchProjectError(project=project_id)

    return project