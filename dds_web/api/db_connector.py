"""API DB Connector module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import traceback
import os

# Installed
import flask
import sqlalchemy
import botocore

# Own modules
from dds_web.database import models
from dds_web import db
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.errors import (
    DatabaseError,
    BucketNotFoundError,
    EmptyProjectException,
    S3ProjectNotFoundError,
    UserDeletionError,
)
import dds_web.utils

####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


class DBConnector:
    """Class for performing database actions."""

    def __init__(self, project=None):
        self.project = project

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    @staticmethod
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
