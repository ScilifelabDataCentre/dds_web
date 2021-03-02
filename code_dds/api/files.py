"""Files module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
import flask_restful
import flask
import sqlalchemy

# Own modules
from code_dds.api.user import token_required
from code_dds.common.db_code import models
from code_dds import db
from code_dds.api.project import project_access_required
from code_dds.api import api_s3_connector
from code_dds.api import db_connector

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


class NewFile(flask_restful.Resource):
    """Inserts a file into the database"""
    method_decorators = [project_access_required, token_required]  # 2, 1

    def post(self, current_user, project):
        """Add new file to DB"""

        args = flask.request.args
        if not all(x in args for x in ["name", "name_in_bucket", "subpath", "size"]):
            return flask.make_response("Information missing, "
                                       "cannot add file to database.", 500)

        try:
            # Check if file already in db
            existing_file = models.File.query.filter_by(
                name=args["name"], project_id=project["id"]
            ).with_entities(models.File.id).first()

            if existing_file or existing_file is not None:
                return flask.make_response(f"File '{args['name']}' already "
                                           "exists in the database!", 500)

            # Add new file to db
            new_file = models.File(name=args["name"],
                                   name_in_bucket=args["name_in_bucket"],
                                   subpath=args["subpath"],
                                   size=args["size"],
                                   project_id=project["id"])
            db.session.add(new_file)
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(
                f"Failed to add new file '{args['name']}' to database: {err}",
                500
            )

        return flask.jsonify({"message": f"File '{args['name']}' added to db."})


class MatchFiles(flask_restful.Resource):
    """Checks for matching files in database"""
    method_decorators = [project_access_required, token_required]  # 2, 1

    def get(self, current_user, project):
        """Matches specified files to files in db."""

        try:
            matching_files = models.File.query.filter(
                models.File.name.in_(flask.request.json)
            ).filter_by(project_id=project["id"]).all()
        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(
                f"Failed to get matching files in db: {err}", 500
            )

        # The files checked are not in the db
        if not matching_files or matching_files is None:
            return flask.jsonify({"files": None})

        return flask.jsonify({"files": list(x.name for x in matching_files)})


class ListFiles(flask_restful.Resource):
    """Lists files within a project"""
    method_decorators = [project_access_required, token_required]

    def get(self, current_user, project):
        """Get a list of files within the specified folder."""

        args = flask.request.args

        # Check project not empty
        num_files, message = self.project_size(project=project["id"])
        if message != "":
            return flask.make_response(message, 500)
        if num_files == 0:
            return flask.jsonify(
                {"num_items": num_files,
                 "message": f"The project {project['id']} is empty."}
            )

        # Check if to return file size
        show_size = False
        if "show_size" in args and args["show_size"] == "True":
            show_size = True

        # Check if to get from root or folder
        subpath = "."
        if "subpath" in args:
            subpath = args["subpath"]

        # Get files and folders
        distinct_files, distinct_folders = self.items_in_subpath(project=project,
                                                                 folder=subpath)

        # Collect file and folder info to return to CLI
        files_folders = list()
        if distinct_files:
            for x in distinct_files:
                info = {"name": x[0] if subpath == "."
                        else x[0].split(subpath + "/")[-1],
                        "folder": False}
                if show_size:
                    info.update({"size": self.fix_size_format(num_bytes=x[1])})
                files_folders.append(info)
        if distinct_folders:
            for x in distinct_folders:
                info = {"name": x[0] if subpath == "."
                        else x[0].split(subpath + "/")[-1],
                        "folder": True}
                if show_size:
                    folder_size = self.folder_size(project=project["id"],
                                                   folder_name=x[0])
                    info.update(
                        {"size": fix_size_format(num_bytes=folder_size)}
                    )
                files_folders.append(info)

        return flask.jsonify({"files_folders": files_folders})

    @staticmethod
    def items_in_subpath(project, folder="."):
        """Get all items in root folder of project"""

        # Get everything in root:
        # Files have subpath "." and folders do not have child folders
        # Get everything in folder:
        # Files have subpath == folder and folders have child folders (regexp)
        try:
            # All files in project
            files = models.File.query.filter_by(
                project_id=project["id"]
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
            return flask.make_response(
                f"Failed to get files from database: {err}", 500
            )

        return distinct_files, distinct_folders

    @staticmethod
    def folder_size(project, folder_name="."):
        """Get total size of folder"""

        try:
            file_info = models.File.query.with_entities(
                sqlalchemy.func.sum(models.File.size).label("sizeSum")
            ).filter(
                sqlalchemy.and_(
                    models.File.project_id == project,
                    models.File.subpath.like(f"{folder_name}%")
                )
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(
                f"Failed to get project info from database: {err}", 500
            )

        return file_info.sizeSum

    @staticmethod
    def project_size(project):
        """Get size of project"""

        try:
            num_proj_files = models.Project.query.filter_by(id=project)\
                .with_entities(models.Project.project_files).count()
        except sqlalchemy.exc.SQLAlchemyError as err:
            return 0, err

        return num_proj_files, ""

    @staticmethod
    def fix_size_format(num_bytes):
        """Change size to kb, mb or gb"""

        BYTES = 1
        KB = 1e3
        MB = 1e6
        GB = 1e9

        print(num_bytes, flush=True)
        print(f"type: {type(num_bytes)}", flush=True)
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

        altered = int(num_bytes/chosen_format[0])
        return str(altered), chosen_format[-1]


class RemoveFile(flask_restful.Resource):
    """Removes files from the database and s3 with boto3."""
    method_decorators = [project_access_required, token_required]

    def delete(self, current_user, project):
        """Deletes the files"""

        print(flask.request.json, flush=True)

        with api_s3_connector.ApiS3Connector(
            project_id=project["id"], safespring_project=current_user.safespring
        ) as s3conn:
            if None in [s3conn.url, s3conn.keys, s3conn.bucketname]:
                    return flask.make_response(
                        "No s3 info returned! " + s3conn.message, 500
                    )
            
            for x in flask.request.json:
                # 1- Remove from db
                
                # 2. Remove from s3
                removed, message = s3conn.remove_one(file=x)

                # commit db

                # if issue rollbakc




        return flask.jsonify({"test": "test"})
