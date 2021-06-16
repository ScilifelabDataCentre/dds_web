"""Files module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import os

# Installed
import flask_restful
import flask
import sqlalchemy
from sqlalchemy.sql import func

# Own modules
from dds_web import timestamp, app
from dds_web.database import models
from dds_web import db, timestamp
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.db_connector import DBConnector
from dds_web.api.dds_decorators import token_required, project_access_required

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


class NewFile(flask_restful.Resource):
    """Inserts a file into the database"""

    method_decorators = [project_access_required, token_required]  # 2, 1

    def post(self, _, project):
        """Add new file to DB"""

        message = ""
        required_info = [
            "name",
            "name_in_bucket",
            "subpath",
            "size",
            "size_processed",
            "compressed",
            "salt",
            "public_key",
            "checksum",
        ]
        args = flask.request.args
        if not all(x in args for x in required_info):
            missing = [x for x in required_info if x not in args]
            return flask.make_response(
                f"Information missing ({missing}), cannot add file to database.", 500
            )

        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(project["id"])
            ).first()

            # Check if file already in db
            existing_file = (
                models.File.query.filter(
                    sqlalchemy.and_(
                        models.File.name == func.binary(args["name"]),
                        models.File.project_id == func.binary(current_project.id),
                    )
                )
                .with_entities(models.File.id)
                .first()
            )

            if existing_file or existing_file is not None:
                return flask.make_response(
                    f"File '{args['name']}' already exists in the database!", 500
                )

            # Add new file to db
            new_file = models.File(
                public_id=os.urandom(16).hex(),
                name=args["name"],
                name_in_bucket=args["name_in_bucket"],
                subpath=args["subpath"],
                size_original=args["size"],
                size_stored=args["size_processed"],
                compressed=bool(args["compressed"] == "True"),
                salt=args["salt"],
                public_key=args["public_key"],
                time_uploaded=timestamp(),
                checksum=args["checksum"],
                project_id=current_project,
            )
            current_project.files.append(new_file)
            db.session.add(new_file)
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            app.logger.debug(err)
            db.session.rollback()
            return flask.make_response(
                f"Failed to add new file '{args['name']}' to database: {err}", 500
            )

        return flask.jsonify({"message": f"File '{args['name']}' added to db."})

    def put(self, _, project):

        args = flask.request.args
        if not all(x in args for x in ["name", "name_in_bucket", "subpath", "size"]):
            return flask.make_response("Information missing, " "cannot add file to database.", 500)

        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(project["id"])
            ).first()

            # Check if file already in db
            existing_file = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.name == func.binary(args["name"]),
                    models.File.project_id == current_project.id,
                )
            ).first()

            # Error if not found
            if not existing_file or existing_file is None:
                return flask.make_response(
                    f"Cannot update non-existent file '{args['name']}' in the database!",
                    500,
                )

            old_size = existing_file.size_original

            # Update file info
            existing_file.subpath = args["subpath"]
            existing_file.size_original = args["size"]
            existing_file.size_stored = args["size_processed"]
            existing_file.compressed = bool(args["compressed"] == "True")
            existing_file.salt = args["salt"]
            existing_file.public_key = args["public_key"]
            existing_file.time_uploaded = timestamp()
            existing_file.checksum = args["checksum"]

            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            return flask.make_response(f"Failed updating file information: {err}", 500)

        return flask.jsonify({"message": f"File '{args['name']}' updated in db."})


class MatchFiles(flask_restful.Resource):
    """Checks for matching files in database"""

    method_decorators = [project_access_required, token_required]  # 2, 1

    def get(self, _, project):
        """Matches specified files to files in db."""

        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(project["id"])
            ).first()

            matching_files = (
                models.File.query.filter(models.File.name.in_(flask.request.json))
                .filter(models.File.project_id == func.binary(current_project.id))
                .all()
            )
        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(f"Failed to get matching files in db: {err}", 500)

        # The files checked are not in the db
        if not matching_files or matching_files is None:
            return flask.jsonify({"files": None})

        return flask.jsonify({"files": {x.name: x.name_in_bucket for x in matching_files}})


class ListFiles(flask_restful.Resource):
    """Lists files within a project"""

    method_decorators = [project_access_required, token_required]

    def get(self, current_user, project):
        """Get a list of files within the specified folder."""

        args = flask.request.args
        if project["permission"] != "ls":
            app.logger.debug("User does not have listing permissions.")
            return flask.make_response(
                f"User {current_user.username} does not have permission to list project contents.",
                401,
            )

        # Check if to return file size
        show_size = False
        if "show_size" in args and args["show_size"] == "True":
            show_size = True

        # Check if to get from root or folder
        subpath = "."
        if "subpath" in args:
            subpath = args["subpath"].rstrip(os.sep)

        files_folders = list()

        # Check project not empty
        with DBConnector() as dbconn:
            # Get number of files in project and return if empty or error
            num_files, error = dbconn.project_size()
            if num_files == 0:
                if error != "":
                    return flask.make_response(error, 500)

                return flask.jsonify(
                    {
                        "num_items": num_files,
                        "message": f"The project {project['id']} is empty.",
                    }
                )

            # Get files and folders
            distinct_files, distinct_folders, error = dbconn.items_in_subpath(folder=subpath)

            if error != "":
                return flask.make_response(error, 500)

            # Collect file and folder info to return to CLI
            if distinct_files:
                for x in distinct_files:
                    info = {
                        "name": x[0] if subpath == "." else x[0].split(os.sep)[-1],
                        "folder": False,
                    }
                    if show_size:
                        info.update({"size": self.fix_size_format(num_bytes=x[1])})
                    files_folders.append(info)
            if distinct_folders:
                for x in distinct_folders:
                    info = {
                        "name": x if subpath == "." else x.split(os.sep)[-1],
                        "folder": True,
                    }

                    if show_size:
                        folder_size, error = dbconn.folder_size(folder_name=x)
                        if folder_size is None:
                            return flask.make_response(error, 500)

                        info.update({"size": self.fix_size_format(num_bytes=folder_size)})
                    files_folders.append(info)

        return flask.jsonify({"files_folders": files_folders})

    @staticmethod
    def fix_size_format(num_bytes):
        """Change size to kb, mb or gb"""

        BYTES = 1
        KB = 1e3
        MB = 1e6
        GB = 1e9

        num_bytes = int(num_bytes)
        chosen_format = [None, ""]
        if num_bytes > GB:
            chosen_format = [GB, "GB"]
        elif num_bytes > MB:
            chosen_format = [MB, "MB"]
        elif num_bytes > KB:
            chosen_format = [KB, "KB"]
        else:
            chosen_format = [BYTES, "bytes"]

        altered = int(round(num_bytes / chosen_format[0]))
        return str(altered), chosen_format[-1]


class RemoveFile(flask_restful.Resource):
    """Removes files from the database and s3 with boto3."""

    method_decorators = [project_access_required, token_required]

    def delete(self, _, project):
        """Deletes the files"""

        with DBConnector() as dbconn:
            not_removed_dict, not_exist_list, error = dbconn.delete_multiple(
                files=flask.request.json
            )

            # S3 connection error
            if not any([not_removed_dict, not_exist_list]) and error != "":
                return flask.make_response(error, 500)

        # Return deleted and not deleted files
        return flask.jsonify({"not_removed": not_removed_dict, "not_exists": not_exist_list})


class RemoveDir(flask_restful.Resource):
    """Removes one or more full directories from the database and s3."""

    method_decorators = [project_access_required, token_required]

    def delete(self, current_user, project):
        """Deletes the folders."""

        not_removed_dict, not_exist_list = ({}, [])

        with DBConnector() as dbconn:
            with ApiS3Connector() as s3conn:
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

        return flask.jsonify({"not_removed": not_removed_dict, "not_exists": not_exist_list})


class FileInfo(flask_restful.Resource):
    """Get file info on files to download."""

    method_decorators = [project_access_required, token_required]

    def get(self, _, project):
        """Checks which files can be downloaded, and get their info."""

        # Get files and folders requested by CLI
        paths = flask.request.json

        files_single, files_in_folders = ({}, {})

        # Get info on files and folders
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(project["id"])
            ).first()

            # Get all files in project
            files_in_proj = models.File.query.filter(
                models.File.project_id == func.binary(current_project.id)
            )

            # All files matching the path -- single files
            files = (
                files_in_proj.filter(models.File.name.in_(paths))
                .with_entities(
                    models.File.name,
                    models.File.name_in_bucket,
                    models.File.subpath,
                    models.File.size_original,
                    models.File.size_stored,
                    models.File.salt,
                    models.File.public_key,
                    models.File.checksum,
                    models.File.compressed,
                )
                .all()
            )

            # All paths which start with the subpath are within a folder
            for x in paths:
                # Only try to match those not already saved in files
                if x not in [f[0] for f in files]:
                    list_of_files = (
                        files_in_proj.filter(models.File.subpath.like(f"{x.rstrip(os.sep)}%"))
                        .with_entities(
                            models.File.name,
                            models.File.name_in_bucket,
                            models.File.subpath,
                            models.File.size_original,
                            models.File.size_stored,
                            models.File.salt,
                            models.File.public_key,
                            models.File.checksum,
                            models.File.compressed,
                        )
                        .all()
                    )

                    if list_of_files:
                        files_in_folders[x] = [tuple(x) for x in list_of_files]

        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(str(err), 500)
        else:

            # Make dict for files with info
            files_single = {
                x[0]: {
                    "name_in_bucket": x[1],
                    "subpath": x[2],
                    "size_original": x[3],
                    "size_stored": x[4],
                    "key_salt": x[5],
                    "public_key": x[6],
                    "checksum": x[7],
                    "compressed": x[8],
                }
                for x in files
            }

        try:
            return flask.jsonify({"files": files_single, "folders": files_in_folders})
        except Exception as err:
            print(str(err), flush=True)


class FileInfoAll(flask_restful.Resource):
    """Get info on all project files."""

    method_decorators = [project_access_required, token_required]

    def get(self, _, project):
        """Get file info."""

        files = {}
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(project["id"])
            ).first()

            all_files = (
                models.File.query.filter_by(project_id=current_project.id)
                .with_entities(
                    models.File.name,
                    models.File.name_in_bucket,
                    models.File.subpath,
                    models.File.size_original,
                    models.File.size_stored,
                    models.File.salt,
                    models.File.public_key,
                    models.File.checksum,
                    models.File.compressed,
                )
                .all()
            )
        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(str(err), 500)
        else:
            if all_files is None or not all_files:
                return flask.make_response(f"The project {project['id']} is empty.", 401)

            files = {
                x[0]: {
                    "name_in_bucket": x[1],
                    "subpath": x[2],
                    "size_original": x[3],
                    "size_stored": x[4],
                    "key_salt": x[5],
                    "public_key": x[6],
                    "checksum": x[7],
                    "compressed": x[8],
                }
                for x in all_files
            }

        return flask.jsonify({"files": files})


class UpdateFile(flask_restful.Resource):
    """Update file info after download"""

    method_decorators = [project_access_required, token_required]

    def put(self, _, project):
        """Update info in db."""

        # Get file name from request from CLI
        file_name = flask.request.args
        if "name" not in file_name:
            return flask.make_response("No file name specified. Cannot update file.", 500)

        # Update file info
        try:
            current_project = models.Project.query.filter(
                models.Project.public_id == func.binary(project["id"])
            ).first()

            app.logger.debug("Updating file in current project: %s", current_project.public_id)

            file = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.project_id == func.binary(current_project.id),
                    models.File.name == func.binary(file_name["name"]),
                )
            ).first()

            if not file:
                return flask.make_response(f"No such file: {file_name['name']}", 500)

            file.time_latest_download = timestamp()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            app.logger.exception(str(err))
            return flask.make_response(str(err), 500)
        else:
            app.logger.debug("File %s updated", file_name["name"])
            db.session.commit()

        return flask.jsonify({"message": "File info updated."})
