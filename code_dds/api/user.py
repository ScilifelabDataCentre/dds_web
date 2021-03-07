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
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################

def token_required(f):
    """Decorator function for verifying the JWT tokens in requests."""

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get the token from the header
        if "x-access-token" in flask.request.headers:
            token = flask.request.headers["x-access-token"]

        # Deny access if token is missing
        if token is None or not token:
            return flask.jsonify({"message": "Token is missing!"}), 401

        # Verify the token
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"])
            table = models.Facility if data["facility"] else models.User
            current_user = table.query.filter_by(
                public_id=data["public_id"]
            ).first()
            print(f"Current user {current_user}", flush=True)
        except Exception:
            return flask.jsonify({"message": "Token is invalid!"}), 401

        return f(current_user, *args, **kwargs)

    return decorated


class AuthenticateUser(flask_restful.Resource):
    """Handles the authentication of the user."""

    def get(self):
        """Checks the username, password and generates the token."""

        # Get username and password from CLI request
        auth = flask.request.authorization
        if not auth or not auth.username or not auth.password:
            return flask.make_response("Could not verify", 401)

        # Check for user and which table to work in
        try:
            role = models.Role.query.filter_by(username=auth.username).\
                with_entities(models.Role.facility).first()
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            return flask.make_response(
                f"Database connection failed - {sqlerr}", 500
            )

        # Deny access if there is no such user
        if not role:
            return flask.make_response(f"User does not exist: {auth.username}",
                                       401)

        # Get user from DB matching the username
        try:
            table = models.Facility if role[0] else models.User
            user = table.query.filter_by(username=auth.username).first()
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            return flask.make_response(
                f"Database connection failed - {sqlerr}", 500
            )

        # Deny access if there is no such user
        if not user:
            return flask.make_response(
                f"User role registered as '{'facility' if role[0] else 'user'}'"
                " but user account not found! User denied access: "
                f"{auth.username}", 401
            )

        # Verify user password and generate token
        if verify_password_argon2id(user.password, auth.password):
            token = jwt.encode(
                {"public_id": user.public_id,
                 "facility": role[0],
                 "exp": datetime.datetime.utcnow() +
                 datetime.timedelta(hours=48)},
                app.config["SECRET_KEY"]
            )

            return flask.jsonify({"token": token.decode("UTF-8")})

        return flask.make_response("Could not verify", 401)
