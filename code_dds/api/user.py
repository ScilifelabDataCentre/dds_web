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
            table = models.Facility if data["facility"] == "True" \
                else models.User
            current_user = table.query.filter_by(
                public_id=data["public_id"]
            ).first()
            print(f"Current user {current_user}", flush=True)
        except Exception:
            return flask.jsonify({"message": "Token is invalid!"}), 401

        return f(current_user, *args, **kwargs)

    return decorated


def gen_argon2hash(password, time_cost=2, memory_cost=102400, parallelism=8,
                   hash_len=32, salt_len=16, encoding="utf-8",
                   version=argon2.low_level.Type.ID):

    pw_hasher = argon2.PasswordHasher(time_cost=time_cost,
                                      memory_cost=memory_cost,
                                      parallelism=parallelism,
                                      hash_len=hash_len,
                                      salt_len=salt_len,
                                      encoding=encoding,
                                      type=version)

    formated_hash = pw_hasher.hash(password)
    return formated_hash


class AuthenticateUser(flask_restful.Resource):
    """Handles the authentication of the user."""

    def get(self):
        """Checks the username, password and generates the token."""

        # Get username and password from CLI request
        auth = flask.request.authorization
        if not auth or not auth.username or not auth.password:
            return flask.make_response("Could not verify", 401)

        args = flask.request.args
        if "facility" not in args:
            return flask.make_response("Could not verify, missing information",
                                       401)

        # Get user from DB matching the username
        try:
            table = models.Facility if args["facility"] == "True" \
                else models.User
            user = table.query.filter_by(username=auth.username).first()

        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            return flask.make_response(
                f"Database connection failed - {sqlerr}", 500
            )

        # Deny access if there is no such user
        if not user:
            return flask.make_response(f"User does not exist: {auth.username}",
                                       401)

        if verify_password_argon2id(user.password, auth.password):
            token = jwt.encode(
                {"public_id": user.public_id,
                 "facility": args["facility"],
                 "exp": datetime.datetime.utcnow() +
                 datetime.timedelta(hours=48)},
                app.config["SECRET_KEY"]
            )

            return flask.jsonify({"token": token.decode("UTF-8")})

        return flask.make_response("Could not verify", 401)


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

    return True
