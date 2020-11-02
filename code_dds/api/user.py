"""User related API endpoints."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
import flask
import flask_restful

# Own modules
from code_dds import marshmallows as marmal
from code_dds import models
from code_dds.api import login


###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################

class LoginUser(flask_restful.Resource):
    """Handles the access checks on the users."""

    # TODO (senthil): use @marshal_with instead of jsonify etc. Worked first
    # but stopped working for some reason. Gives response 500.
    def post(self):
        """Checks the users access to the delivery system.

        Args:
            username:   Username
            password:   Password
            project:    Project ID
            owner:      Owner of project with project ID

        Returns:
            json:   access (bool), s3_id (str), public_key (str),
                    error (str), project_id (int), token (str)
        """

        # Get args from request
        user_info = flask.request.args

        # Look for user in database
        ok, uid, error = login.ds_access(username=user_info["username"],
                                   password=user_info["password"],
                                   role=0)
        if not ok:  # Access denied
            return flask.jsonify(access=False,
                           user_id=uid,
                           s3_id="",
                           public_key=None,
                           error=error,
                           project_id=user_info["project"],
                           token="")

        # Look for project in database
        ok, public_key, error = login.project_access(uid=uid,
                                               project=user_info["project"],
                                               owner=user_info["username"], 
                                               role="user")
        if not ok:  # Access denied
            return flask.jsonify(access=False,
                           user_id=uid,
                           s3_id="",
                           public_key=None,
                           error=error,
                           project_id=user_info["project"],
                           token="")

        # Get S3 project ID for project
        ok, s3_id, error = login.cloud_access(project=user_info["project"])
        if not ok:  # Access denied
            return flask.jsonify(access=False,
                           user_id=uid,
                           s3_id=s3_id,
                           public_key=None,
                           error=error,
                           project_id=user_info["project"],
                           token="")

        # Generate delivery token
        token = login.gen_access_token(project=user_info["project"])

        # Access approved
        return flask.jsonify(access=True,
                       user_id=uid,
                       s3_id=s3_id,
                       public_key=public_key,
                       error="",
                       project_id=user_info["project"],
                       token=token)


class ListUsers(flask_restful.Resource):
    """Lists all users in database."""

    def get(self):
        """Gets all users from db and return them in response."""

        all_users = models.User.query.all()
        return marmal.users_schema.dump(all_users)
