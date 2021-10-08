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
from sqlalchemy.sql import func

# Own modules
import dds_web.utils
from dds_web import auth
from dds_web.utils import verify
from dds_web.database import models
from dds_web import db
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.db_connector import DBConnector
from dds_web.api.errors import DatabaseError
from dds_web.api import marshmallows

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class NewFile(flask_restful.Resource):
    """Inserts a file into the database"""

    @auth.login_required
    def post(self):
        """Add new file to DB."""

        new_file, new_version, project = marshmallows.NewFileSchema().load(
            {**flask.request.json, **flask.request.args}
        )

        try:
            # Update foreign keys
            project.file_versions.append(new_version)
            project.files.append(new_file)
            new_file.versions.append(new_version)

            # db.session.add(new_file)
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            flask.current_app.logger.debug(err)
            db.session.rollback()
            return flask.make_response(f"Failed to add new file to database.", 500)

        return flask.jsonify({"message": f"File '{new_file.name}' added to db."})

    @auth.login_required
    def put(self):

        args = flask.request.args

        project = verify(
            current_user=auth.current_user(),
            project_public_id=args.get("project"),
            endpoint_methods=["put"],
        )

        if not all(x in args for x in ["name", "name_in_bucket", "subpath", "size"]):
            return flask.make_response("Information missing, " "cannot add file to database.", 500)

        try:
            # Check if file already in db
            existing_file = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.name == func.binary(args["name"]),
                    models.File.project_id == project.id,
                )
            ).first()

            # Error if not found
            if not existing_file or existing_file is None:
                return flask.make_response(
                    f"Cannot update non-existent file '{args['name']}' in the database!",
                    500,
                )

            # Get version row
            current_file_version = models.Version.query.filter(
                sqlalchemy.and_(
                    models.Version.active_file == func.binary(existing_file.id),
                    models.Version.time_deleted == None,
                )
            ).all()
            if len(current_file_version) > 1:
                flask.current_app.logger.warning(
                    "There is more than one version of the file which does not yet have a deletion timestamp."
                )

            # Same timestamp for deleted and created new file
            new_timestamp = dds_web.utils.current_time()

            # Overwritten == deleted/deactivated
            for version in current_file_version:
                if version.time_deleted is None:
                    version.time_deleted = new_timestamp

            # Update file info
            existing_file.subpath = args["subpath"]
            existing_file.size_original = args["size"]
            existing_file.size_stored = args["size_processed"]
            existing_file.compressed = bool(args["compressed"] == "True")
            existing_file.salt = args["salt"]
            existing_file.public_key = args["public_key"]
            existing_file.time_uploaded = new_timestamp
            existing_file.checksum = args["checksum"]

            # New version
            new_version = models.Version(
                size_stored=args["size_processed"],
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
            return flask.make_response(f"Failed updating file information: {err}", 500)

        return flask.jsonify({"message": f"File '{args['name']}' updated in db."})


class MatchFiles(flask_restful.Resource):
    """Checks for matching files in database"""

    @auth.login_required
    def get(self):
        """Matches specified files to files in db."""

        files = marshmallows.ExistingFilesSchema().load(flask.request.args)

        return flask.jsonify(
            {"files": {f.name: f.name_in_bucket for f in files} if files else None}
        )


class ListFiles(flask_restful.Resource):
    """Lists files within a project"""

    @auth.login_required
    def get(self):
        """Get a list of files within the specified folder."""

        args = flask.request.args

        project = verify(
            current_user=auth.current_user(),
            project_public_id=args.get("project"),
            endpoint_methods=["ls"],
        )

        # Check if to return file size
        show_size = args.get("show_size") == "True"

        # Check if to get from root or folder
        subpath = args.get("subpath").rstrip(os.sep) if args.get("subpath") else "."

        files_folders = list()

        # Check project not empty
        with DBConnector(project=project) as dbconn:
            # Get number of files in project and return if empty or error
            try:
                num_files = dbconn.project_size()
            except DatabaseError:
                raise

            if num_files == 0:
                return flask.jsonify(
                    {
                        "num_items": num_files,
                        "message": f"The project {project.public_id} is empty.",
                    }
                )

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

        return flask.jsonify({"files_folders": files_folders})


class RemoveFile(flask_restful.Resource):
    """Removes files from the database and s3 with boto3."""

    @auth.login_required
    def delete(self):
        """Deletes the files"""

        args = flask.request.args

        project = verify(
            current_user=auth.current_user(),
            project_public_id=args.get("project"),
            endpoint_methods=["rm"],
        )

        with DBConnector(project=project) as dbconn:
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

    @auth.login_required
    def delete(self):
        """Deletes the folders."""

        args = flask.request.args

        project = verify(
            current_user=auth.current_user(),
            project_public_id=args.get("project"),
            endpoint_methods=["rm"],
        )

        not_removed_dict, not_exist_list = ({}, [])

        try:
            with DBConnector(project=project) as dbconn:

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
        except (ValueError,):
            raise
        return flask.jsonify({"not_removed": not_removed_dict, "not_exists": not_exist_list})


class FileInfo(flask_restful.Resource):
    """Get file info on files to download."""

    @auth.login_required
    def get(self):
        """Checks which files can be downloaded, and get their info."""

        args = flask.request.args

        project = verify(
            current_user=auth.current_user(),
            project_public_id=args.get("project"),
            endpoint_methods=["get"],
        )

        # Get files and folders requested by CLI
        paths = flask.request.json

        files_single, files_in_folders = ({}, {})

        # Get info on files and folders
        try:
            # Get all files in project
            files_in_proj = models.File.query.filter(
                models.File.project_id == func.binary(project.id)
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
            flask.current_app.logger.exception(str(err))


class FileInfoAll(flask_restful.Resource):
    """Get info on all project files."""

    @auth.login_required
    def get(self):
        """Get file info."""

        args = flask.request.args

        project = verify(
            current_user=auth.current_user(),
            project_public_id=args.get("project"),
            endpoint_methods=["get"],
        )

        files = {}
        try:
            all_files = (
                models.File.query.filter_by(project_id=project.id)
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
                return flask.make_response(f"The project {project.public_id} is empty.", 401)

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

    @auth.login_required
    def put(self):
        """Update info in db."""

        args = flask.request.args

        project = verify(
            current_user=auth.current_user(),
            project_public_id=args.get("project"),
            endpoint_methods=["get"],
        )

        # Get file name from request from CLI
        file_name = args.get("name")
        if not file_name:
            return flask.make_response("No file name specified. Cannot update file.", 500)

        # Update file info
        try:
            flask.current_app.logger.debug(
                "Updating file in current project: %s", project.public_id
            )

            file = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.project_id == func.binary(project.id),
                    models.File.name == func.binary(file_name["name"]),
                )
            ).first()

            if not file:
                return flask.make_response(f"No such file: {file_name['name']}", 500)

            file.time_latest_download = dds_web.utils.current_time()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            flask.current_app.logger.exception(str(err))
            return flask.make_response(str(err), 500)
        else:
            flask.current_app.logger.debug("File %s updated", file_name["name"])
            db.session.commit()

        return flask.jsonify({"message": "File info updated."})
