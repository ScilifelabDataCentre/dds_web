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
from jwcrypto import jwk, jwt

# Own modules
from dds_web.api.errors import AuthenticationError, AccessDeniedError
from dds_web.database import models
from dds_web import basic_auth, token_auth

####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


@basic_auth.error_handler
def auth_error(status):
    return auth_error_common(status)


@token_auth.error_handler
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


@token_auth.get_user_roles
def get_user_roles(user):
    return get_user_roles_common(user)


def get_user_roles_common(user):
    """Return the users role as saved in the db."""

    return user.role


@token_auth.verify_token
def verify_token(token):
    data = (
        verify_token_signature(token)
        if token.count(".") == 2
        else decrypt_and_verify_token_signature(token)
    )
    expiration_time = data.get("exp")
    # we use a hard check on top of the one from the dependency
    # exp shouldn't be before now no matter what
    if datetime.datetime.now() <= datetime.datetime.fromtimestamp(expiration_time):
        username = data.get("sub")
        if username:
            user = models.User.query.get(username)
            if user:
                return user
        return None
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
    user = models.User.query.get(username)
    if user and verify_password_argon2id(user.password, password):
        return user
    return None


def gen_argon2hash(
    password,
    time_cost=2,
    memory_cost=102400,
    parallelism=8,
    hash_len=32,
    salt_len=16,
    encoding="utf-8",
    version=argon2.low_level.Type.ID,
):
    """Generates Argon2id password hash to store in DB."""

    pw_hasher = argon2.PasswordHasher(
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
        hash_len=hash_len,
        salt_len=salt_len,
        encoding=encoding,
        type=version,
    )
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
    except (
        argon2.exceptions.VerifyMismatchError,
        argon2.exceptions.VerificationError,
        argon2.exceptions.InvalidHash,
    ):
        return False

    # TODO (ina): Add check_needs_rehash?

    return True
