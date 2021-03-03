"""API DB Connector module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import traceback

# Installed
import flask
import sqlalchemy

# Own modules
from code_dds.api.errors import BucketNameNotFoundError, ProjectSizeError, \
    DBFileError, FolderSizeError, FileDeletionError, FileRetrievalError
from code_dds.common.db_code import models
from code_dds import db
from code_dds.api.dds_decorators import token_required

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

        try:
            bucket = models.Project.query.filter_by(
                id=self.project["id"]
            ).with_entities(
                models.Project.bucket
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise BucketNameNotFoundError from err

        return bucket

    def project_size(self):
        """Get size of project"""

        try:
            num_proj_files = models.Project.query.filter_by(
                id=self.project["id"]
            ).with_entities(models.Project.project_files).count()
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise ProjectSizeError from err

        return num_proj_files

    def items_in_subpath(self, folder="."):
        """Get all items in root folder of project"""

        # Get everything in root:
        # Files have subpath "." and folders do not have child folders
        # Get everything in folder:
        # Files have subpath == folder and folders have child folders (regexp)
        try:
            # All files in project
            files = models.File.query.filter_by(
                project_id=self.project["id"]
            )

            # File names in root
            distinct_files = files.filter(
                models.File.subpath == folder
            ).with_entities(
                models.File.name, models.File.size
            ).all()

            # Folder names in folder (or root)
            distinct_folders = files.filter(
                sqlalchemy.and_(
                    (~models.File.subpath.contains(["/"]) if folder == "."
                     else
                     models.File.subpath.op("regexp")(f"^{folder}(\/[^\/]+)?$")),
                    models.File.subpath != folder
                )
            ).with_entities(models.File.subpath).distinct().all()
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DBFileError from err

        return distinct_files, distinct_folders

    def folder_size(self, folder_name="."):
        """Get total size of folder"""

        try:
            file_info = models.File.query.with_entities(
                sqlalchemy.func.sum(models.File.size).label("sizeSum")
            ).filter(
                sqlalchemy.and_(
                    models.File.project_id == self.project["id"],
                    models.File.subpath.like(f"{folder_name}%")
                )
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise FolderSizeError from err

        return file_info.sizeSum

    def delete_all(self):
        """Delete all files in project."""

        deleted, error = (False, "")
        try:
            models.File.query.filter_by(project_id=self.project["id"]).delete()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            error = str(err)
        else:
            deleted = True

        return deleted, error

    def delete_one(self, filename):
        """Delete all files in project."""

        deleted, error = (False, "")
        try:
            file = models.File.query.filter_by(
                name=filename,
                project_id=self.project["id"]
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            error = str(err)
                
        if file and file is not None:
            try:
                db.session.delete(file)
            except sqlalchemy.exc.SQLAlchemyError as err:
                db.session.rollback()
                error = str(err)
            else:
                deleted = True

        return deleted, error
