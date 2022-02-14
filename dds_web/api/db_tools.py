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
)

####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


def remove_user_self_deletion_request(user):

    try:
        request_row = models.DeletionRequest.query.filter(
            models.DeletionRequest.requester_id == user.username
        ).one_or_none()
        if not request_row:
            raise UserDeletionError("There is no deletion request from this user.")

        email = request_row.email
        db.session.delete(request_row)
        db.session.commit()
    except sqlalchemy.exc.SQLAlchemyError as err:
        db.session.rollback()
        raise DatabaseError(message=str(err))

    return email
