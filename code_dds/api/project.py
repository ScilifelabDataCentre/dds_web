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
from code_dds.common.db_code import models

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


class ProjectAccess(flask_restful.Resource):
    """Checks a users access to a specific project."""
    method_decorators = [token_required]

    def get(self, current_user):
        """Checks the users access to a specific project and action."""

        args = flask.request.args

        # Deny access if project or method not specified
        if "project" not in args or "method" not in args:
            return flask.make_response("Invalid request", 500)

        # Check if user is allowed to performed attempted operation
        try:
            user = models.Role.query.filter_by(username=current_user.username).\
                with_entities(models.Role.facility).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(
                f"Failed getting user role information from database: {err}",
                500
            )

        # Error if user not found - should not be able to happen since logged in
        if user is None or not user:
            return flask.make_response(
                "Did not find user in database. Error in delivery system.", 500
            )

        # Facilities can upload and list, users can download and list
        # TODO (ina): Add allowed actions to DB instead of hard coding
        if (user[0] and args["method"] not in ["put"]) or \
                (not user[0] and args["method"] not in ["get"]):
            return flask.make_response(
                f"Attempted to {args['method']} in project {args['project']}. "
                "Permission denied.", 401
            )

        # Check if user has access to project
        if args["project"] in [x.id for x in current_user.user_projects]:
            return flask.jsonify({"dds-access-granted": True})

        return flask.make_response("Project access denied", 401)
