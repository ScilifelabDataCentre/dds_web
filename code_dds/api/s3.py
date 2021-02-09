"""S3 module"""

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

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################

class S3Info(flask_restful.Resource):
    """Gets the projects S3 keys"""
    method_decorators = [token_required]

    def get(self, current_user):
        """Get the safespring project"""

        # Get project ID
        project = flask.request.args
        if "project" not in project:
            return flask.make_response("Invalid request", 500)

        # Extra check for project access
        if project["project"] not in [x.id for x in current_user.user_projects]:
            return flask.make_response("Project access denied!", 401)

        # Get Safespring project
        print(current_user.safespring, flush=True)
        return flask.jsonify({"safespring_project": current_user.safespring})