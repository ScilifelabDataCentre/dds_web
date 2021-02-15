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

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


class NewFile(flask_restful.Resource):
    """Checks a users access to a specific project."""
    method_decorators = [token_required]

    def post(self, current_user):
        """Add new file to DB"""

        args = flask.request.args
        if not all(x in args for x in ["name", "name_in_bucket", "subpath", "project"]):
            return flask.make_response("Information missing, "
                                       "cannot add file to database.", 500)

        try:
            new_file = models.File(name=args["name"],
                                   name_in_bucket=args["name_in_bucket"],
                                   subpath=args["subpath"],
                                   project_id=args["project"])
            db.session.add(new_file)
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(
                f"Failed to add new file '{args['name']}' to database: {err}",
                500
            )

        return flask.jsonify({"message": "creating new file"})
