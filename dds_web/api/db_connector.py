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

    def folder_size(self, folder_name="."):
        """Get total size of folder"""

        # Sum up folder file sizes
        try:
            file_info = (
                models.File.query.with_entities(
                    sqlalchemy.func.sum(models.File.size_original).label("sizeSum")
                )
                .filter(
                    sqlalchemy.and_(
                        models.File.project_id == sqlalchemy.func.binary(self.project.id),
                        models.File.subpath.like(f"{folder_name}%"),
                    )
                )
                .first()
            )

        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(message=str(err))
        else:
            return file_info.sizeSum

    def delete_folder(self, folder):
        """Delete all items in folder"""

        exists = False
        deleted = False
        error = ""
        try:
            # File names in root
            files = (
                models.File.query.filter(
                    models.File.project_id == sqlalchemy.func.binary(self.project.id)
                )
                .filter(
                    sqlalchemy.or_(
                        models.File.subpath == sqlalchemy.func.binary(folder),
                        models.File.subpath.op("regexp")(f"^{folder}(\/[^\/]+)*$"),
                    )
                )
                .all()
            )
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(message=str(err))

        if files and files is not None:
            exists = True
            try:
                for x in files:
                    # get current version
                    current_file_version = models.Version.query.filter(
                        sqlalchemy.and_(
                            models.Version.active_file == sqlalchemy.func.binary(x.id),
                            models.Version.time_deleted.is_(None),
                        )
                    ).first()
                    current_file_version.time_deleted = dds_web.utils.current_time()

                    # Delete file and update project size
                    db.session.delete(x)
                self.project.date_updated = dds_web.utils.current_time()
            except sqlalchemy.exc.SQLAlchemyError as err:
                error = str(err)
            else:
                deleted = True

        return exists, deleted, error

    def delete_multiple(self, files):
        """Delete multiple files."""

        not_removed_dict, not_exist_list, error = ({}, [], "")

        with ApiS3Connector(project=self.project) as s3conn:

            # Delete each file
            for x in files:
                # Delete from db
                in_db, delete_ok, name_in_bucket, error = self.delete_one(filename=x)

                # Non existant files cannot be deleted
                if not in_db:
                    not_exist_list.append(x)
                    continue

                # Failure to delete
                if not delete_ok or name_in_bucket is None:
                    db.session.rollback()
                    not_removed_dict[x] = error
                    continue

                # Remove from s3 bucket
                try:
                    s3conn.remove_one(file=name_in_bucket)
                except (BucketNotFoundError, botocore.client.ClientError) as err:
                    db.session.rollback()
                    not_removed_dict[x] = str(err)
                    continue

                # Commit to db if ok
                try:
                    db.session.commit()
                except sqlalchemy.exc.SQLAlchemyError as err:
                    db.session.rollback()
                    not_removed_dict[x] = str(err)
                    continue

        return not_removed_dict, not_exist_list, error

    def delete_one(self, filename):
        """Delete a single file in project."""

        exists, deleted, name_in_bucket, error = (False, False, None, "")

        # Get matching files in project
        try:
            file = models.File.query.filter(
                models.File.name == sqlalchemy.func.binary(filename),
                models.File.project_id == sqlalchemy.func.binary(self.project.id),
            ).first()

        except sqlalchemy.exc.SQLAlchemyError as err:
            error = str(err)

        # Delete if found, but do not commit yet
        if file or file is not None:
            exists, name_in_bucket = (True, file.name_in_bucket)
            try:
                # TODO (ina): put in own class

                # get current version
                current_file_version = models.Version.query.filter(
                    sqlalchemy.and_(
                        models.Version.active_file == sqlalchemy.func.binary(file.id),
                        models.Version.time_deleted.is_(None),
                    )
                ).first()
                current_file_version.time_deleted = dds_web.utils.current_time()

                db.session.delete(file)
                self.project.date_updated = dds_web.utils.current_time()
            except sqlalchemy.exc.SQLAlchemyError as err:
                db.session.rollback()
                error = str(err)
            else:
                deleted = True

        return exists, deleted, name_in_bucket, error

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
