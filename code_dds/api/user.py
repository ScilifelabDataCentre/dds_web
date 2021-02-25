"""Docstring"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import datetime
import binascii

# Installed
import argon2
import flask
import flask_restful
import jwt
import sqlalchemy
import functools

# Own modules
from code_dds import app
from code_dds.common.db_code import models

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################


def token_required(f):
    """Decorator function for verifying the JWT tokens in requests."""

    @functools.wraps(f)
    def validate_token(*args, **kwargs):
        token = None

        # Get the token from the header
        if "x-access-token" in flask.request.headers:
            token = flask.request.headers["x-access-token"]

        # Deny access if token is missing
        if token is None or not token:
            return flask.jsonify({"message": "Token is missing!"}), 401

        # Verify the token
        try:
            # Decode
            data = jwt.decode(token, app.config["SECRET_KEY"])

            # Get table and user
            table = models.Facility if data["facility"] else models.User
            current_user = table.query.filter_by(
                public_id=data["public_id"]
            ).first()

            project = data["project"]
        except Exception:
            return flask.jsonify({"message": "Token is invalid!"}), 401

        return f(current_user, project, *args, **kwargs)

    return validate_token

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


def gen_argon2hash(password, time_cost=2, memory_cost=102400, parallelism=8,
                   hash_len=32, salt_len=16, encoding="utf-8",
                   version=argon2.low_level.Type.ID):
    """Generates Argon2id password hash to store in DB."""

    pw_hasher = argon2.PasswordHasher(time_cost=time_cost,
                                      memory_cost=memory_cost,
                                      parallelism=parallelism,
                                      hash_len=hash_len,
                                      salt_len=salt_len,
                                      encoding=encoding,
                                      type=version)
    formated_hash = pw_hasher.hash(password)

    return formated_hash


def verify_password_argon2id(db_pw, input_pw):
    """Verifies that the password specified by the user matches
    the encoded password in the database."""

    # Setup Argon2 hasher
    password_hasher = argon2.PasswordHasher()

    # Verify the input password
    try:
        password_hasher.verify(db_pw, input_pw)
    except (argon2.exceptions.VerifyMismatchError,
            argon2.exceptions.VerificationError,
            argon2.exceptions.InvalidHash) as err:
        print(err, flush=True)
        return False

    # TODO: Add check_needs_rehash?

    return True


def is_facility(username):
    """Checks if the user is a facility or not."""

    # Check for user and which table to work in
    try:
        role = models.Role.query.filter_by(username=username).\
            with_entities(models.Role.facility).first()
    except sqlalchemy.exc.SQLAlchemyError as sqlerr:
        return flask.make_response(
            f"Database connection failed - {sqlerr}", 500
        )

    # Deny access if there is no such user
    if not role or role is None:
        return None

    return role[0]


def jwt_token(user_id, is_fac, project_id, project_access=False):
    """Generates and encodes a JWT token."""

    token = jwt.encode(
        {"public_id": user_id,
         "facility": is_fac,
         "project": {"id": project_id, "verified": project_access},
         "exp": datetime.datetime.utcnow() +
         datetime.timedelta(hours=48)},
        app.config["SECRET_KEY"]
    )

    return token


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
        user_is_fac = is_facility(username=auth.username)
        if user_is_fac is None:
            return flask.make_response(f"User does not exist: {auth.username}",
                                       401)

        # Get user from DB matching the username
        try:
            table = models.Facility if user_is_fac else models.User
            user = table.query.filter_by(username=auth.username).first()
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            return flask.make_response(
                f"Database connection failed - {sqlerr}", 500
            )

        # Deny access if there is no such user
        if not user:
            return flask.make_response(
                "User role registered as "
                f"'{'facility' if user_is_fac else 'user'}' but user account "
                f"not found! User denied access: {auth.username}", 401
            )

        # Verify user password and generate token
        if verify_password_argon2id(user.password, auth.password):
            token = jwt_token(user_id=user.public_id,
                              is_fac=user_is_fac,
                              project_id=project)

            return flask.jsonify({"token": token.decode("UTF-8")})

        return flask.make_response("Incorrect password!", 401)
