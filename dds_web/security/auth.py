"""Authentication related functions/tools."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Installed
import datetime
import argon2
import http
import flask
import json
import jwcrypto
from jwcrypto import jwk, jwt
import structlog

# Own modules
from dds_web.errors import AuthenticationError, AccessDeniedError
from dds_web.database import models
from dds_web import basic_auth, auth
import dds_web.utils

action_logger = structlog.getLogger("actions")
####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


@basic_auth.error_handler
def auth_error(status):
    return auth_error_common(status)


@auth.error_handler
def auth_error(status):
    return auth_error_common(status)


def auth_error_common(status):
    if status == http.HTTPStatus.UNAUTHORIZED:
        raise AuthenticationError()
    elif status == http.HTTPStatus.FORBIDDEN:
        raise AccessDeniedError(message="Insufficient credentials")


@basic_auth.get_user_roles
def get_user_roles(user):
    return get_user_roles_common(user)


@auth.get_user_roles
def get_user_roles(user):
    return get_user_roles_common(user)


def get_user_roles_common(user):
    """Return the users role as saved in the db."""

    return user.role


@auth.verify_token
def verify_token(token):
    try:
        data = (
            verify_token_signature(token)
            if token.count(".") == 2
            else decrypt_and_verify_token_signature(token)
        )
    except (ValueError, jwcrypto.common.JWException) as e:
        # ValueError is raised when the token doesn't look right (for example no periods)
        # jwcryopto.common.JWException is the base exception raised by jwcrypto,
        # and is raised when the token is malformed or invalid.
        flask.current_app.logger.exception(
            e
        )  # TODO log this to specific file to track failed attempts
        raise AuthenticationError(message="Invalid token")

    expiration_time = data.get("exp")
    # we use a hard check on top of the one from the dependency
    # exp shouldn't be before now no matter what
    if dds_web.utils.current_time() <= datetime.datetime.fromtimestamp(expiration_time):
        username = data.get("sub")
        if username:
            user = models.User.query.get(username)
        return user or None
    raise AuthenticationError(message="Expired token")


def extract_encrypted_token_content(token, username):
    """Extract the sensitive content from inside the encrypted token"""
    content = decrypt_and_verify_token_signature(token)
    return content.get("sen_con") if content.get("sub") == username else None


def decrypt_and_verify_token_signature(token):
    """Wrapper function that streamlines decryption and signature verification,
    and returns the claims"""
    return verify_token_signature(decrypt_token(token))


def decrypt_token(token):
    """Decrypt the encrypted token and return
    the signed token embedded inside"""
    key = jwk.JWK.from_password(flask.current_app.config.get("SECRET_KEY"))
    decrypted_token = jwt.JWT(key=key, jwt=token)
    return decrypted_token.claims


def verify_token_signature(token):
    """Verify the signature of the token and return the claims
    such as subject/username on valid signature"""
    key = jwk.JWK.from_password(flask.current_app.config.get("SECRET_KEY"))
    try:
        jwttoken = jwt.JWT(key=key, jwt=token, algs=["HS256"])
        return json.loads(jwttoken.claims)
    except jwt.JWTExpired:
        # jwt dependency uses a 60 seconds leeway to check exp
        # it also prints out a stack trace for it, so we handle it here
        raise AuthenticationError(message="Expired token")


@basic_auth.verify_password
def verify_password(username, password):
    """Verify that user exists and that password is correct."""
    user = models.User.query.get(username)
    if user and user.verify_password(input_password=password):
        return user
    return None
