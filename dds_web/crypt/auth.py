"""Password related cryptography stuff"""

import argon2

import sqlalchemy

from dds_web.database import models
from sqlalchemy.sql import func
from dds_web import exceptions
from flask import session
from dds_web.api.errors import InvalidUserCredentialsError, DatabaseError


def verify_user_pass(username, password):
    """Verify that user exists and password is correct."""

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
