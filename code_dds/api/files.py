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
from code_dds.api.project import is_verified

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


class NewFile(flask_restful.Resource):
    """Inserts a file into the database"""
    method_decorators = [token_required]

    def post(self, current_user, project):
        """Add new file to DB"""

        project_verified, message = is_verified(project=project)
        if not project_verified:
            return flask.make_response(message, 401)

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
    method_decorators = [token_required]

    def get(self, current_user, project):
        """Matches specified files to files in db."""

        project_verified, message = is_verified(project=project)
        if not project_verified:
            return flask.make_response(message, 401)

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
