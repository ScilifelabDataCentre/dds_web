"""Project module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import functools

# Installed
import flask_restful
import flask
import sqlalchemy

# Own modules
from code_dds.api.user import token_required
from code_dds.api.user import jwt_token
from code_dds.api.user import is_facility
from code_dds.common.db_code import models
from code_dds import timestamp

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################


def project_access_required(f):

    @functools.wraps(f)
    def verify_project_access(current_user, project, *args, **kwargs):
        """Verifies that the user has been granted access to the project."""

        if project["id"] is None:
            return flask.make_response(
                "Project ID missing. Cannot proceed", 401
            )

        if not project["verified"]:
            return flask.make_response(
                f"Access to project {project['id']} not yet verified. "
                "Checkout token settings.", 401
            )

        return f(current_user, project, *args, **kwargs)

    return verify_project_access


###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################


class ProjectAccess(flask_restful.Resource):
    """Checks a users access to a specific project."""
    method_decorators = [token_required]

    def get(self, current_user, project):
        """Checks the users access to a specific project and action."""

        args = flask.request.args

        # Deny access if project or method not specified
        if "method" not in args:
            return flask.make_response("Invalid request", 500)

        # Check if user is allowed to performed attempted operation
        user_is_fac = is_facility(username=current_user.username)
        if user_is_fac is None:
            return flask.make_response(
                f"User does not exist: {current_user.username}", 401
            )

        # Facilities can upload and list, users can download and list
        # TODO (ina): Add allowed actions to DB instead of hard coding
        if (user_is_fac and args["method"] not in ["put"]) or \
                (not user_is_fac and args["method"] not in ["get"]):
            return flask.make_response(
                f"Attempted to {args['method']} in project {project['id']}. "
                "Permission denied.", 401
            )

        # Check if user has access to project
        if project["id"] in [x.id for x in current_user.user_projects]:
            token = jwt_token(user_id=current_user.public_id,
                              is_fac=user_is_fac, project_id=project["id"],
                              project_access=True)
            return flask.jsonify({"dds-access-granted": True, "token": token.decode("UTF-8")})

        return flask.make_response("Project access denied", 401)


class UserProjects(flask_restful.Resource):
    """Gets all projects registered to a specific user."""
    method_decorators = [token_required]

    def get(self, current_user, *args):
        """Get info regarding all projects which user is involved in."""

        # TODO: Return different things depending on if facility or not
        print(current_user.user_projects, flush=True)
        user_is_fac = is_facility(username=current_user.username)
        if user_is_fac is None:
            return flask.make_response(
                f"User does not exist: {current_user.username}", 401
            )

        all_projects = list()
        columns = ["Project ID", "Title", "PI", "Status", "Last updated"]
        for x in current_user.user_projects:
            all_projects.append({columns[0]: x.id,
                                 columns[1]: x.title,
                                 columns[2]: x.pi,
                                 columns[3]: x.status,
                                 columns[4]: timestamp(
                                     datetime_string=x.date_updated
                                     )}
            )
        return flask.jsonify({"all_projects": all_projects, "columns": columns})
