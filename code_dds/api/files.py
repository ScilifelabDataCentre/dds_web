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

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


class NewFile(flask_restful.Resource):
    """Inserts a file into the database"""
    method_decorators = [project_access_required, token_required]  # 2, 1

    def post(self, current_user, project):
        """Add new file to DB"""

        args = flask.request.args
        if not all(x in args for x in ["name", "name_in_bucket", "subpath"]):
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
        show_size = False
        if "show_size" in args and args["show_size"]:
            show_size = True

        subpath = ""
        if "subpath" not in args:
            distinct_files, distinct_folders = items_in_root(project=project)

        else:
            subpath = args["subpath"]
            distinct_files, distinct_folders = items_in_folder(project=project,
                                                               subpath=subpath)

        # Collect file and folder info to return to CLI
        files_folders = list()
        if distinct_files:
            for x in distinct_files:
                files_folders.append(
                    {"name": x.name if subpath == ""
                     else x.name.split(subpath + "/")[-1],
                     "folder": False}
                )
        if distinct_folders:
            for x in distinct_folders:
                files_folders.append(
                    {"name": x[0] if subpath == ""
                     else x[0].split(subpath + "/")[-1],
                     "folder": True}
                )

        return flask.jsonify({"files_folders": files_folders})


def items_in_root(project):
    """Get all items in root folder of project"""

    # Get everything in root:
    # Files have subpath "." and folders do not have child folders
    try:
        # All files in project
        files = models.File.query.filter_by(
            project_id=project["id"]
        )

        # File names in root
        distinct_files = files.filter(models.File.subpath == ".").all()

        # Folder names in root (unique)
        distinct_folders = files.filter(
            sqlalchemy.and_(
                ~models.File.subpath.contains(["/"]),
                models.File.subpath != "."
            )
        ).with_entities(models.File.subpath).distinct().all()
    except sqlalchemy.exc.SQLAlchemyError as err:
        return flask.make_response(
            f"Failed to get files from database: {err}", 500
        )

    return distinct_files, distinct_folders


def items_in_folder(project, subpath):
    """Get all items in a folder within the project."""

    # Get everything in subpath:
    # Files have subpath == subpath and folders have child folders
    try:
        # All files in project
        files = models.File.query.filter_by(
            project_id=project["id"]
        )

        # File names in subpath
        distinct_files = files.filter(
            models.File.subpath == subpath
        ).all()

        # Folder names in subpath
        distinct_folders = files.filter(
            sqlalchemy.and_(
                models.File.subpath.op("regexp")(
                    f"^{subpath}(\/[^\/]+)?$"
                ),
                models.File.subpath != subpath
            )
        ).with_entities(models.File.subpath).distinct().all()
    except sqlalchemy.exc.SQLAlchemyError as err:
        return flask.make_response(
            f"Failed to get files from database: {err}", 500
        )

    return distinct_files, distinct_folders
