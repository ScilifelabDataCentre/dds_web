"""API DB Connector module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import traceback
import os
import time

# Installed
import flask
import sqlalchemy
from sqlalchemy.sql import func

# Own modules
from dds_web import timestamp, app
from dds_web.database import models
from dds_web import db
from dds_web.api.dds_decorators import token_required
from dds_web.api.api_s3_connector import ApiS3Connector

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


@token_required
class DBConnector:
    """Class for performing database actions."""

    def __init__(self, *args, **kwargs):

        try:
            self.current_user, self.project = args
        except ValueError as err:
            flask.abort(500, str(err))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def get_bucket_name(self):
        """Get bucket name from database"""

        bucketname, error = (None, "")
        try:
            bucket = (
                models.Project.query.filter(
                    models.Project.public_id == func.binary(self.project["id"])
                )
                .with_entities(models.Project.bucket)
                .first()
            )
            app.logger.debug("Bucket: %s", bucket)
        except sqlalchemy.exc.SQLAlchemyError as err:
            error = str(err)
        else:
            bucketname = bucket[0]

        return bucketname, error

    def filename_in_bucket(self, filename):
        """Get filename in bucket."""

        name_in_bucket, error = (None, "")
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == self.project["id"]
            ).first()

            file = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.project_id == func.binary(current_project.id),
                    models.File.name == func.binary(filename),
                )
            ).first()

            app.logger.debug("--------File: %s", file)
        except sqlalchemy.exc.SQLAlchemyError as err:
            error = str(err)
        else:
            name_in_bucket = file[0]

        return name_in_bucket, error

    def project_size(self):
        """Get size of project"""

        num_proj_files, error = (0, "")
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(self.project["id"])
            ).first()

            num_proj_files = models.File.query.filter(
                models.File.project_id == func.binary(current_project.id)
            ).count()

            app.logger.debug("Number of project files: %s", num_proj_files)
        except sqlalchemy.exc.SQLAlchemyError as err:
            error = str(err)

        return num_proj_files, error

    # def update_project_size(self, new_size):

    #     updated, error, current_try, max_retries = (False, "", 0, 5)

    #     while current_try < max_retries:
    #         try:
    #             current_project = models.Project.query.filter_by(id=self.project["id"]).first()
    #             if not current_project or current_project is None:
    #                 return updated, f"Could not find project {self.project['id']}!"

    #             current_project.size += int(new_size)
    #             current_project.date_updated = timestamp()
    #             db.session.commit()
    #         except sqlalchemy.exc.SQLAlchemyError as err:
    #             print(f"{current_try}: Trying again....", flush=True)
    #             db.session.rollback()
    #             error = str(err)
    #             current_try += 1
    #             time.sleep(2)
    #         else:
    #             updated, error = (True, "")
    #             print(f"OK! Updated on {current_try}/{max_retries}")
    #             break

    # current_project = models.Project.query.filter_by(id=project["id"]).first()
    # if not current_project or current_project is None:
    #     return flask.make_response(f"Could not find project {project['id']}!")
    # current_project.size += old_size - int(args["size"])
    # current_project.date_updated = timestamp()
    # db.session.commit()

    #     return updated, error

    def items_in_subpath(self, folder="."):
        """Get all items in root folder of project"""

        distinct_files, distinct_folders, error = ([], [], "")
        # Get everything in root:
        # Files have subpath "." and folders do not have child folders
        # Get everything in folder:
        # Files have subpath == folder and folders have child folders (regexp)
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(self.project["id"])
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
            error = str(err)

        return distinct_files, distinct_folders, error

    def folder_size(self, folder_name="."):
        """Get total size of folder"""

        tot_file_size, error = (None, "")
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(self.project["id"])
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
            error = str(err)
        else:
            tot_file_size = file_info.sizeSum

        return tot_file_size, error

    def delete_all(self):
        """Delete all files in project."""

        deleted, error = (False, "")
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(self.project["id"])
            ).first()

            num_deleted = models.File.query.filter(
                models.File.project_id == current_project.id
            ).delete()

            # TODO (ina): put in class
            # change project size
            current_project.size = 0
            current_project.date_updated = timestamp()
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            error = str(err)
        else:
            if num_deleted == 0:
                error = f"There are no files within project {self.project['id']}."
                deleted = False
            else:
                deleted = True

        return deleted, error

    def delete_folder(self, folder):
        """Delete all items in folder"""

        exists, deleted, error = (False, False, "")
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
            error = str(err)

        if files and files is not None:
            exists = True
            try:
                current_project = models.Project.query.filter(
                    models.Project.public_id == func.binary(self.project["id"])
                ).first()
                for x in files:
                    old_size = x.size_original
                    db.session.delete(x)
                    current_project.size -= old_size
                current_project.date_updated = timestamp()
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
                db.session.delete(file)
                current_project.size -= old_size
                current_project.date_updated = timestamp()
            except sqlalchemy.exc.SQLAlchemyError as err:
                db.session.rollback()
                error = str(err)
            else:
                deleted = True

        return exists, deleted, name_in_bucket, error

    def delete_dir(self, foldername):
        """Delete all files in a folder"""

        exists, deleted, errors = (False, None, None)

        # Get files in folder
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(self.project["id"])
            ).first()

            files_in_folder = models.File.query.filter(
                models.File.project_id == func.binary(current_project.id),
                models.File.subpath == func.binary(foldername),
            ).all()
        except sqlalchemy.exc.SQLAlchemyError as err:
            error = str(err)

        # Get bucket info and delete files
        if files_in_folder or files_in_folder is not None:
            exists, deleted, errors = (True, {}, {})
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(self.project["id"])
            ).first()
            for x in files_in_folder:
                filename = x.name
                nameinbucket = x.name_in_bucket
                size = x.size_original
                try:
                    db.session.delete(x)
                except sqlalchemy.exc.SQLAlchemyError as err:
                    db.session.rollback()
                    errors[filename] = str(err)
                else:
                    current_project.size -= size
                    deleted[filename] = {"name_in_bucket": nameinbucket}
            current_project.date_updated = timestamp()
        return exists, deleted, errors

    def cloud_project(self):
        """Get safespring project"""

        sfsp_proj, error = ("", "")

        # Get current project
        try:

            current_project_facility_safespring = (
                models.Project.query.join(
                    models.Facility, models.Project.facility_id == func.binary(models.Facility.id)
                )
                .add_columns(models.Facility.safespring)
                .filter(models.Facility.id == func.binary(models.Project.facility_id))
                .filter(models.Project.public_id == func.binary(self.project["id"]))
            ).first()

            app.logger.debug("Safespring project: %s", current_project_facility_safespring)
            if not current_project_facility_safespring:
                error = "No safespring project found for responsible facility."

            sfsp_proj = current_project_facility_safespring[1]
        except sqlalchemy.exc.SQLAlchemyError as err:
            error = str(err)

        return sfsp_proj, error
