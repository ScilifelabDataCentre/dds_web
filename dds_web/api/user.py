"""Docstring"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import datetime
import binascii

# Installed
import flask
import flask_restful
import jwt
import sqlalchemy
import functools
from sqlalchemy.sql import func

# Own modules
from dds_web import app
from dds_web.database import models
from dds_web.crypt.auth import gen_argon2hash, verify_password_argon2id

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


def is_facility(username):
    """Checks if the user is a facility or not."""

    is_fac, error = (False, "")
    print(f"Username: {username}", flush=True)
    # Check for user and which table to work in
    try:
        role = (
            models.Role.query.filter(models.Role.username == func.binary(username))
            .with_entities(models.Role.facility)
            .first()
        )
        # user = models.Role.query.filter(models.Role.username.is_(username)).first()
        # print(user, flush=True)
    except sqlalchemy.exc.SQLAlchemyError as sqlerr:
        error = f"Database connection failed - {sqlerr}" + str(sqlerr)
    else:
        # Deny access if there is no such user
        if not role or role is None:
            is_fac, error = (None, "The user doesn't exist.")
        else:
            is_fac = role[0]

    return is_fac, error


def jwt_token(user_id, project_id, project_access=False, permission="ls"):
    """Generates and encodes a JWT token."""

    token, error = (None, "")
    try:
        token = jwt.encode(
            {
                "public_id": user_id,
                "project": {"id": project_id, "verified": project_access, "permission": permission},
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=48),
            },
            app.config["SECRET_KEY"],
        )
    except Exception as err:
        token, error = (None, str(err))

    return token, error


###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################


class AuthenticateUser(flask_restful.Resource):
    """Handles the authentication of the user."""

    def get(self):
        """Checks the username, password and generates the token."""

        # Get username and password from CLI request
        auth = flask.request.authorization
        if not auth or not auth.username or not auth.password:
            return flask.make_response("Could not verify", 401)
        app.logger.debug(auth)

        # Project not required, will be checked for future operations
        args = flask.request.args
        if "project" not in args:
            project = None
        else:
            project = args["project"]
        app.logger.debug(project)

        # Check if user in db
        try:
            user = models.User.query.filter(
                models.User.username == func.binary(auth.username)
            ).first()
            app.logger.debug(user)
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            return flask.make_response(f"Database connection failed: {sqlerr}", 500)

        app.logger.debug(not user)
        if not user:
            return flask.make_response(
                f"User not found in system. User access denied: {auth.username}", 401
            )

        # Verify user password and generate token
        if verify_password_argon2id(user.password, auth.password):
            if "l" not in list(user.permissions):
                return flask.make_response(
                    f"The user {auth.username} does not have any permissions", 401
                )

            token, error = jwt_token(user_id=user.public_id, project_id=project)
            if token is None:
                return flask.make_response(error, 500)

            # Success - return token
            return flask.jsonify({"token": token.decode("UTF-8")})

        # Failed - incorrect password
        return flask.make_response("Incorrect password!", 401)
