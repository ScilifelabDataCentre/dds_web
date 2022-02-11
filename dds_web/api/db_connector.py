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
    def delete_user(user):

        try:
            parent_user = models.User.query.get(user.username)
            db.session.delete(parent_user)
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            raise DatabaseError(message=str(err))

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

    @staticmethod
    def project_usage(project_object):

        bhours = 0.0
        cost = 0.0

        for v in project_object.file_versions:
            # Calculate hours of the current file
            time_deleted = v.time_deleted if v.time_deleted else dds_web.utils.current_time()
            time_uploaded = v.time_uploaded

            file_hours = (time_deleted - time_uploaded).seconds / (60 * 60)

            # Calculate BHours
            bhours += v.size_stored * file_hours

            # Calculate approximate cost per gbhour: kr per gb per month / (days * hours)
            cost_gbhour = 0.09 / (30 * 24)

            # Save file cost to project info and increase total unit cost
            cost += bhours / 1e9 * cost_gbhour

        return bhours, cost
