"""Password related cryptography stuff"""

import argon2
import jwt
import sqlalchemy

from jwt import DecodeError

from dds_web.database import models
from sqlalchemy.sql import func
from dds_web import app, basic_auth, exceptions, token_auth
from dds_web.api.errors import InvalidUserCredentialsError, DatabaseError


@basic_auth.get_user_roles
def get_user_roles(user):
    return get_user_roles_common(user)


@token_auth.get_user_roles
def get_user_roles(user):
    return get_user_roles_common(user)


def get_user_roles_common(user):
    if "a" in user.permissions:
        return "admin"
    else:
        return "user"


@token_auth.verify_token
def verify_token(token):
    try:
        data = jwt.decode(token, app.config.get("SECRET_KEY"), algorithms="HS256")
        username = data.get("user")
        if username:
            user = models.User.query.get(username)
            if user:
                return user
        return None
    except DecodeError:
        return None


@basic_auth.verify_password
def verify_password(username, password):
    user = models.User.query.get(username)
    if user and verify_password_argon2id(user.password, password):
        return user
    return None


def verify_user_pass(username, password):
    """DEPRECATED (WILL BE REPLACED): Verify that user exists and password is correct."""

    # Verify existing user
    try:
        user = models.User.query.filter(models.User.username == username).first()
    except sqlalchemy.exc.SQLAlchemyError as sqlerr:
        raise DatabaseError(message=str(sqlerr), username=username)

    # User exists and password correct
    if user and verify_password_argon2id(user.password, password):
        return True

    raise InvalidUserCredentialsError(username=username)


def user_session_info(username):
    """Gets session info about the user."""

    # Get user role and facility ID
    try:
        user = (
            models.User.query.filter(models.User.username == func.binary(username))
            .with_entities(models.User.role, models.User.facility_id)
            .first()
        )
    except sqlalchemy.exc.SQLAlchemyError:
        raise

    # Raise exception if there is no user
    if not user:
        raise exceptions.DatabaseInconsistencyError("Unable to retrieve user role.")

    # Setup session info default
    user_info = {"current_user": username, "is_facility": False, "is_admin": False}

    # Admin and facility specific info
    if user[0] == "admin":
        user_info["is_admin"] = True
    elif user[0] == "facility":
        if not user[1]:
            raise exceptions.DatabaseInconsistencyError(
                "Missing facility ID for facility type user."
            )

        # Get facility name from database
        try:
            facility_info = (
                models.Facility.query.filter(models.Facility.id == func.binary(user[1]))
                .with_entities(models.Facility.name)
                .first()
            )
        except sqlalchemy.exc.SQLAlchemyError:
            raise

        user_info.update(
            {"is_facility": True, "facility_id": user[1], "facility_name": facility_info[0]}
        )

    return user_info


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
