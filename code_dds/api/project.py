"""Project module."""

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
from code_dds.db_code import models

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


class ProjectAccess(flask_restful.Resource):
    """Checks a users access to a specific project."""
    method_decorators = [token_required]

    def get(self, current_user):
        """Docstring"""

        args = flask.request.args
        if "project" not in args:
            return flask.make_response("Invalid request", 500)

        if args["project"] in [x.id for x in current_user.user_projects]:
            return flask.jsonify({"dds-access-granted": True})

        return flask.make_response("Project access denied", 401)

