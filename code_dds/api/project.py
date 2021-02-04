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

    @token_required
    def post(self):
        """Docstring"""

        # print(current_user, flush=True)
        return flask.make_response("Testing", 200)