"""API DB Connector module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import traceback
import os
import time
import datetime

# Installed
import flask  # used
import sqlalchemy
from sqlalchemy.sql import func

# Own modules
from dds_web.database import models
from dds_web import db
from dds_web.api.dds_decorators import token_required
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.errors import (
    MissingTokenOutputError,
    DatabaseError,
    BucketNotFoundError,
    EmptyProjectException,
    NoSuchProjectError,
    S3ProjectNotFoundError,
)
import dds_web.utils

####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


@token_required
class DBConnector:
    """Class for performing database actions."""

    def __init__(self, *args, **kwargs):

        try:
            self.current_user, self.project = args
        except ValueError as err:
            raise MissingTokenOutputError(message=str(err))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def get_bucket_name(self):
        """Get bucket name from database"""

        project_id = self.project.get("id")
        if not project_id:
            raise MissingTokenOutputError(
                message="Project ID not found. Cannot get project bucket."
            )

        # Get bucket from db
        try:
            bucket = (
                models.Project.query.filter(models.Project.public_id == func.binary(project_id))
                .with_entities(models.Project.bucket)
                .first()
            )

            if not bucket:
                raise BucketNotFoundError

            bucketname = bucket[0]

            flask.current_app.logger.debug("Bucket: %s", bucket)
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(message=str(err))
        else:
            return bucketname

    def project_size(self):
        """Get size (number of files in) of project"""

        project_id = self.project.get("id")
        if not project_id:
            raise MissingTokenOutputError(
                message="Project ID not found. Cannot get project bucket."
            )

        # Check the number of files in the project
        # TODO (ina): fix join
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(project_id)
            ).first()

            num_proj_files = models.File.query.filter(
                models.File.project_id == func.binary(current_project.id)
            ).count()

            flask.current_app.logger.debug("Number of project files: %s", num_proj_files)
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(message=str(err))
        else:
            return num_proj_files

    def items_in_subpath(self, folder="."):
        """Get all items in root folder of project"""

        project_id = self.project.get("id")
        if not project_id:
            raise MissingTokenOutputError(
                message="Project ID not found. Cannot get project bucket."
            )

        distinct_files = []
        distinct_folders = []
        # Get everything in root:
        # Files have subpath "." and folders do not have child folders
        # Get everything in folder:
        # Files have subpath == folder and folders have child folders (regexp)
        # TODO (ina): fix join
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(project_id)
            ).first()

            # All files in project
            files = models.File.query.filter(
                models.File.project_id == func.binary(current_project.id)
            )

            # File names in root
            distinct_files = (
                files.filter(models.File.subpath == func.binary(folder))
                .with_entities(models.File.name, models.File.size_original)
                .all()
            )

            # Folder names in folder (or root)
            if folder == ".":
                # Get distinct folders in root, subpath should not be "."
                distinct_folders = (
                    files.filter(models.File.subpath != func.binary(folder))
                    .with_entities(models.File.subpath)
                    .distinct()
                    .all()
                )

                # Get first subpath (may be many and first may not have files in)
                first_parts = set(x[0].split(os.sep)[0] for x in distinct_folders)
                distinct_folders = list(first_parts)
            else:
                # Get distinct sub folders in specific folder with regex
                distinct_folders = (
                    files.filter(models.File.subpath.op("regexp")(f"^{folder}(\/[^\/]+)+$"))
                    .with_entities(models.File.subpath)
                    .distinct()
                    .all()
                )

                # Get length of specified folder
                len_folder = len(folder.split(os.sep))

                # Get subfolders in level under specified folder
                split_paths = set(
                    f"{os.sep}".join(x[0].split(os.sep)[: len_folder + 1]) for x in distinct_folders
                )
                distinct_folders = list(split_paths)

        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(message=str(err))
        else:
            return distinct_files, distinct_folders

    def folder_size(self, folder_name="."):
        """Get total size of folder"""

        project_id = self.project.get("id")
        if not project_id:
            raise MissingTokenOutputError(
                message="Project ID not found. Cannot get project bucket."
            )

        # Sum up folder file sizes
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(project_id)
            ).first()

            file_info = (
                models.File.query.with_entities(
                    sqlalchemy.func.sum(models.File.size_original).label("sizeSum")
                )
                .filter(
                    sqlalchemy.and_(
                        models.File.project_id == func.binary(current_project.id),
                        models.File.subpath.like(f"{folder_name}%"),
                    )
                )
                .first()
            )

        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(message=str(err))
        else:
            return file_info.sizeSum

    def delete_all(self):
        """Delete all files in project."""

        project_id = self.project.get("id")
        if not project_id:
            raise MissingTokenOutputError(message="Project ID not found. Cannot delete files.")

        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(project_id)
            ).first()

            num_deleted = models.File.query.filter(
                models.File.project_id == current_project.id
            ).delete()

            # TODO (ina): put in class
            # change project size
            current_project.size = 0
            current_project.date_updated = dds_web.utils.timestamp()
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            raise DatabaseError(message=str(err))
        else:
            if num_deleted == 0:
                raise EmptyProjectException(project=project_id)

            return True

    def delete_folder(self, folder):
        """Delete all items in folder"""

        exists = False
        deleted = False
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(self.project["id"])
            ).first()

            # File names in root
            files = (
                models.File.query.filter(models.File.project_id == func.binary(current_project.id))
                .filter(
                    sqlalchemy.or_(
                        models.File.subpath == func.binary(folder),
                        models.File.subpath.op("regexp")(f"^{folder}(\/[^\/]+)?$"),
                    )
                )
                .all()
            )
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(message=str(err))

        if files and files is not None:
            exists = True
            try:
                current_project = models.Project.query.filter(
                    models.Project.public_id == func.binary(self.project["id"])
                ).first()
                for x in files:
                    # get current version
                    current_file_version = models.Version.query.filter(
                        sqlalchemy.and_(
                            models.Version.active_file == func.binary(x.id),
                            models.Version.time_deleted == None,
                        )
                    ).first()
                    current_file_version.time_deleted = dds_web.utils.timestamp()

                    # Delete file and update project size
                    old_size = x.size_original
                    db.session.delete(x)
                    current_project.size -= old_size
                current_project.date_updated = dds_web.utils.timestamp()
            except sqlalchemy.exc.SQLAlchemyError as err:
                error = str(err)
            else:
                deleted = True

        return exists, deleted, error

    def delete_multiple(self, files):
        """Delete multiple files."""

        not_removed_dict, not_exist_list, error = ({}, [], "")

        with ApiS3Connector() as s3conn:
            # Error if not enough info
            if None in [s3conn.url, s3conn.keys, s3conn.bucketname]:
                return (
                    not_removed_dict,
                    not_exist_list,
                    "No s3 info returned! " + s3conn.message,
                )

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
                delete_ok, error = s3conn.remove_one(file=name_in_bucket)
                if not delete_ok:
                    db.session.rollback()
                    not_removed_dict[x] = error
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
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(self.project["id"])
            ).first()

            file = models.File.query.filter(
                models.File.name == func.binary(filename),
                models.File.project_id == func.binary(current_project.id),
            ).first()

        except sqlalchemy.exc.SQLAlchemyError as err:
            error = str(err)

        # Delete if found, but do not commit yet
        if file or file is not None:
            exists, name_in_bucket = (True, file.name_in_bucket)
            try:
                # TODO (ina): put in own class
                old_size = file.size_original
                current_project = models.Project.query.filter(
                    models.Project.public_id == func.binary(self.project["id"])
                ).first()

                # get current version
                current_file_version = models.Version.query.filter(
                    sqlalchemy.and_(
                        models.Version.active_file == func.binary(file.id),
                        models.Version.time_deleted == None,
                    )
                ).first()
                current_file_version.time_deleted = dds_web.utils.timestamp()

                db.session.delete(file)
                current_project.size -= old_size
                current_project.date_updated = dds_web.utils.timestamp()
            except sqlalchemy.exc.SQLAlchemyError as err:
                db.session.rollback()
                error = str(err)
            else:
                deleted = True

        return exists, deleted, name_in_bucket, error

    def cloud_project(self):
        """Get safespring project"""

        project_id = self.project.get("id")
        if not project_id:
            raise MissingTokenOutputError(message="Project ID not found. Cannot get S3 project.")

        # Get current project
        try:

            current_project_facility_safespring = (
                models.Project.query.join(
                    models.Facility, models.Project.facility_id == func.binary(models.Facility.id)
                )
                .add_columns(models.Facility.safespring)
                .filter(models.Facility.id == func.binary(models.Project.facility_id))
                .filter(models.Project.public_id == func.binary(project_id))
            ).first()

            flask.current_app.logger.debug(
                "Safespring project: %s", current_project_facility_safespring
            )
            if not current_project_facility_safespring:
                raise S3ProjectNotFoundError(
                    message="No safespring project found for responsible facility.",
                    username=self.current_user.username,
                    project=project_id,
                )

            sfsp_proj = current_project_facility_safespring[1]
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(message=str(err))
        else:
            return sfsp_proj

    @staticmethod
    def project_usage(project_object):

        gbhours = 0.0
        cost = 0.0

        for f in project_object.files:
            for v in f.versions:
                # Calculate hours of the current file
                time_uploaded = datetime.datetime.strptime(
                    v.time_uploaded,
                    "%Y-%m-%d %H:%M:%S.%f%z",
                )
                time_deleted = datetime.datetime.strptime(
                    v.time_deleted if v.time_deleted else dds_web.utils.timestamp(),
                    "%Y-%m-%d %H:%M:%S.%f%z",
                )
                file_hours = (time_deleted - time_uploaded).seconds / (60 * 60)

                # Calculate GBHours, if statement to avoid zerodivision exception
                gbhours += ((v.size_stored / 1e9) / file_hours) if file_hours else 0.0

                # Calculate approximate cost per gbhour: kr per gb per month / (days * hours)
                cost_gbhour = 0.09 / (30 * 24)

                # Save file cost to project info and increase total facility cost
                cost += gbhours * cost_gbhour

        return round(gbhours, 2), round(cost, 2)
