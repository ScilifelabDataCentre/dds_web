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

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


class ProjectAccess(flask_restful.Resource):
    """Checks a users access to a specific project."""
    method_decorators = [token_required]

    def post(self, current_user):
        """Docstring"""

        print(f"Current user: {current_user.admin}", flush=True)
        return flask.make_response("Testing", 200)