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

# Own modules
from code_dds import app
from code_dds.db_code import models
from code_dds.crypt.auth import gen_argon2hash, verify_password_argon2id

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


def is_facility(username):
    """Checks if the user is a facility or not."""

    is_fac, error = (False, "")

    # Check for user and which table to work in
    try:
        role = (
            models.Role.query.filter_by(username=username)
            .with_entities(models.Role.facility)
            .first()
        )
    except sqlalchemy.exc.SQLAlchemyError as sqlerr:
        error = f"Database connection failed - {sqlerr}" + str(sqlerr)
    else:
        # Deny access if there is no such user
        if not role or role is None:
            is_fac, error = (None, "The user doesn't exist.")
        else:
            is_fac = role[0]

    return is_fac, error


def jwt_token(user_id, is_fac, project_id, project_access=False):
    """Generates and encodes a JWT token."""

    token, error = (None, "")
    try:
        token = jwt.encode(
            {
                "public_id": user_id,
                "facility": is_fac,
                "project": {"id": project_id, "verified": project_access},
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

        # Project not required, will be checked for future operations
        args = flask.request.args
        if "project" not in args:
            project = None
        else:
            project = args["project"]

        # Check if user has facility role
        user_is_fac, error = is_facility(username=auth.username)
        if user_is_fac is None:
            return flask.make_response(error, 500)

        # Get user from DB matching the username
        try:
            table = models.Facility if user_is_fac else models.User
            user = table.query.filter_by(username=auth.username).first()
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            return flask.make_response(f"Database connection failed: {sqlerr}", 500)

        # Deny access if there is no such user
        if not user or user is None:
            return flask.make_response(
                "User role registered as "
                f"'{'facility' if user_is_fac else 'user'}' but user account "
                f"not found! User denied access: {auth.username}",
                500,
            )

        # Verify user password and generate token
        if verify_password_argon2id(user.password, auth.password):
            token, error = jwt_token(user_id=user.public_id, is_fac=user_is_fac, project_id=project)
            if token is None:
                return flask.make_response(error, 500)

            # Success - return token
            return flask.jsonify({"token": token.decode("UTF-8")})

        # Failed - incorrect password
        return flask.make_response("Incorrect password!", 401)
