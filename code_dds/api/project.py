"""Project module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
import flask_restful
import flask

# Own modules
from code_dds.api.user import token_required
from code_dds.common.db_code import models

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


class ProjectAccess(flask_restful.Resource):
    """Checks a users access to a specific project."""
    method_decorators = [token_required]

    def get(self, current_user):
        """Docstring"""

        args = flask.request.args
        print(f"Project: {args['project']}", flush=True)
        
        # project_info = models


        return flask.make_response("Testing", 200)