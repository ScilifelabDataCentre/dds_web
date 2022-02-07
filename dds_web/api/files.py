"""Files module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import os

# Installed
import flask_restful
import flask
import sqlalchemy
import werkzeug

# Own modules
import dds_web.utils
from dds_web import auth
from dds_web.database import models
from dds_web import db
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.db_connector import DBConnector
from dds_web.api.dds_decorators import logging_bind_request
from dds_web.errors import (
    DatabaseError,
    DDSArgumentError,
    EmptyProjectException,
    NoSuchFileError,
    S3ConnectionError,
)
from dds_web.api.schemas import file_schemas
from dds_web.api.schemas import project_schemas


def check_eligibility_for_upload(status):
    """Check if a project status is eligible for upload/modification"""
    if status != "In Progress":
        raise DDSArgumentError("Project not in right status to upload/modify files.")
    return True


def check_eligibility_for_download(status, user_role):
    """Check if a project status makes it eligible to download"""
    if status == "Available" or (
        status == "In Progress" and user_role in ["Unit Admin", "Unit Personnel"]
    ):
        return True

    raise DDSArgumentError("Current Project status limits file download.")


def check_eligibility_for_deletion(status, has_been_available):
    """Check if a project status is eligible for deletion"""
    if status not in ["In Progress"]:
        raise DDSArgumentError("Project Status prevents files from being deleted.")

    if has_been_available:
        raise DDSArgumentError(
            "Existing project contents cannot be deleted since the project has been previously made available to recipients."
        )
    return True


####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class NewFile(flask_restful.Resource):
    """Inserts a file into the database"""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    def post(self):
        """Add new file to DB"""

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)
        check_eligibility_for_upload(project.current_status)

        new_file = file_schemas.NewFileSchema().load({**flask.request.json, **flask.request.args})

        try:
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            flask.current_app.logger.debug(err)
            db.session.rollback()
            raise DatabaseError(f"Failed to add new file to database.")

        return {"message": f"File '{new_file.name}' added to db."}

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    def put(self):

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        check_eligibility_for_upload(project.current_status)

        file_info = flask.request.json
        if not all(x in file_info for x in ["name", "name_in_bucket", "subpath", "size"]):
            raise DDSArgumentError("Information is missing, cannot add file to database.")

        try:
            # Check if file already in db
            existing_file = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.name == sqlalchemy.func.binary(file_info.get("name")),
                    models.File.project_id == project.id,
                )
            ).first()

            # Error if not found
            if not existing_file or existing_file is None:
                raise NoSuchFileError(
                    "Cannot update non-existent file "
                    f"'{werkzeug.utils.secure_filename(file_info.get('name'))}' in the database!"
                )

            # Get version row
            current_file_version = models.Version.query.filter(
                sqlalchemy.and_(
                    models.Version.active_file == sqlalchemy.func.binary(existing_file.id),
                    models.Version.time_deleted.is_(None),
                )
            ).all()
            if len(current_file_version) > 1:
                flask.current_app.logger.warning(
                    "There is more than one version of the file "
                    "which does not yet have a deletion timestamp."
                )

            # Same timestamp for deleted and created new file
            new_timestamp = dds_web.utils.current_time()

            # Overwritten == deleted/deactivated
            for version in current_file_version:
                if version.time_deleted is None:
                    version.time_deleted = new_timestamp

            # Update file info
            existing_file.subpath = file_info.get("subpath")
            existing_file.size_original = file_info.get("size")
            existing_file.size_stored = file_info.get("size_processed")
            existing_file.compressed = file_info.get("compressed")
            existing_file.salt = file_info.get("salt")
            existing_file.public_key = file_info.get("public_key")
            existing_file.time_uploaded = new_timestamp
            existing_file.checksum = file_info.get("checksum")

            # New version
            new_version = models.Version(
                size_stored=file_info.get("size_processed"),
                time_uploaded=new_timestamp,
                active_file=existing_file.id,
                project_id=project,
            )

            # Update foreign keys and relationships
            project.file_versions.append(new_version)
            existing_file.versions.append(new_version)

            db.session.add(new_version)
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            raise DatabaseError(f"Failed updating file information: {err}")

        return {"message": f"File '{file_info.get('name')}' updated in db."}


class MatchFiles(flask_restful.Resource):
    """Checks for matching files in database"""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    def get(self):
        """Matches specified files to files in db."""

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        check_eligibility_for_upload(project.current_status)

        try:
            matching_files = (
                models.File.query.filter(models.File.name.in_(flask.request.json))
                .filter(models.File.project_id == sqlalchemy.func.binary(project.id))
                .all()
            )
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(f"Failed to get matching files in db: {err}")

        # The files checked are not in the db
        if not matching_files or matching_files is None:
            return {"files": None}

        return {"files": {x.name: x.name_in_bucket for x in matching_files}}


class ListFiles(flask_restful.Resource):
    """Lists files within a project"""

    @auth.login_required
    @logging_bind_request
    def get(self):
        """Get a list of files within the specified folder."""

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)
        extra_args = flask.request.json
        # Check if to return file size
        show_size = extra_args.get("show_size")

        # Check if to get from root or folder
        subpath = "."
        if extra_args.get("subpath"):
            subpath = extra_args.get("subpath").rstrip(os.sep)

        files_folders = list()

        # Check project not empty
        with DBConnector(project=project) as dbconn:
            # Get number of files in project and return if empty
            num_files = project.num_files
            if num_files == 0:
                return {
                    "num_items": num_files,
                    "message": f"The project {project.public_id} is empty.",
                }

            # Get files and folders
            try:
                distinct_files, distinct_folders = dbconn.items_in_subpath(folder=subpath)
            except DatabaseError:
                raise

            # Collect file and folder info to return to CLI
            if distinct_files:
                for x in distinct_files:
                    info = {
                        "name": x[0] if subpath == "." else x[0].split(os.sep)[-1],
                        "folder": False,
                    }
                    if show_size:
                        info.update({"size": dds_web.utils.format_byte_size(x[1])})
                    files_folders.append(info)
            if distinct_folders:
                for x in distinct_folders:
                    info = {
                        "name": x if subpath == "." else x.split(os.sep)[-1],
                        "folder": True,
                    }

                    if show_size:
                        try:
                            folder_size = dbconn.folder_size(folder_name=x)
                        except DatabaseError:
                            raise

                        info.update({"size": dds_web.utils.format_byte_size(folder_size)})
                    files_folders.append(info)

        return {"files_folders": files_folders}


class RemoveFile(flask_restful.Resource):
    """Removes files from the database and s3 with boto3."""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    def delete(self):
        """Deletes the files"""

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        check_eligibility_for_deletion(project.current_status, project.has_been_available)

        with DBConnector(project=project) as dbconn:
            not_removed_dict, not_exist_list, error = dbconn.delete_multiple(
                files=flask.request.json
            )

            # S3 connection error
            if not any([not_removed_dict, not_exist_list]) and error != "":
                raise S3ConnectionError(str(error))

        # Return deleted and not deleted files
        return {"not_removed": not_removed_dict, "not_exists": not_exist_list}


class RemoveDir(flask_restful.Resource):
    """Removes one or more full directories from the database and s3."""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    def delete(self):
        """Deletes the folders."""

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        check_eligibility_for_deletion(project.current_status, project.has_been_available)

        not_removed_dict, not_exist_list = ({}, [])

        try:
            with DBConnector(project=project) as dbconn:

                with ApiS3Connector(project=project) as s3conn:
                    # Error if not enough info
                    if None in [s3conn.url, s3conn.keys, s3conn.bucketname]:
                        return (
                            not_removed_dict,
                            not_exist_list,
                            "No s3 info returned! " + s3conn.message,
                        )

                    for x in flask.request.json:
                        # Get all files in the folder
                        in_db, folder_deleted, error = dbconn.delete_folder(folder=x)

                        if not in_db:
                            db.session.rollback()
                            not_exist_list.append(x)
                            continue

                        # Error with db --> folder error
                        if not folder_deleted:
                            db.session.rollback()
                            not_removed_dict[x] = error
                            continue

                        # Delete from s3
                        folder_deleted, error = s3conn.remove_folder(folder=x)

                        if not folder_deleted:
                            db.session.rollback()
                            not_removed_dict[x] = error
                            continue

                        # Commit to db if no error so far
                        try:
                            db.session.commit()
                        except sqlalchemy.exc.SQLAlchemyError as err:
                            db.session.rollback()
                            not_removed_dict[x] = str(err)
                            continue
        except (ValueError,):
            raise
        return {"not_removed": not_removed_dict, "not_exists": not_exist_list}


class FileInfo(flask_restful.Resource):
    """Get file info on files to download."""

    @auth.login_required
    @logging_bind_request
    def get(self):
        """Checks which files can be downloaded, and get their info."""

        input_ = {**flask.request.args, **{"requested_items": flask.request.json, "url": True}}

        # Get project contents
        found_files, found_folder_contents, not_found = project_schemas.ProjectContentSchema().dump(
            input_
        )

        return {
            "files": found_files,
            "folder_contents": found_folder_contents,
            "not_found": not_found,
        }


class FileInfoAll(flask_restful.Resource):
    """Get info on all project files."""

    @auth.login_required
    @logging_bind_request
    def get(self):
        """Get file info."""

        files, _, _ = project_schemas.ProjectContentSchema().dump(
            {**flask.request.args, "get_all": True, "url": True}
        )

        return {"files": files}


class UpdateFile(flask_restful.Resource):
    """Update file info after download"""

    @auth.login_required
    @logging_bind_request
    def put(self):
        """Update info in db."""

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        file_info = flask.request.json

        # Get file name from request from CLI
        file_name = file_info.get("name")
        if not file_name:
            raise DDSArgumentError("No file name specified. Cannot update file.")

        # Update file info
        try:
            flask.current_app.logger.debug(
                "Updating file in current project: %s", project.public_id
            )

            flask.current_app.logger.debug(f"File name: {file_name}")
            file = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.project_id == sqlalchemy.func.binary(project.id),
                    models.File.name == sqlalchemy.func.binary(file_name),
                )
            ).first()

            if not file:
                raise NoSuchFileError()

            file.time_latest_download = dds_web.utils.current_time()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            flask.current_app.logger.exception(str(err))
            raise DatabaseError("Update of file info failed.")
        else:
            # flask.current_app.logger.debug("File %s updated", file_name)
            db.session.commit()

        return {"message": "File info updated."}
