"""Password related cryptography stuff"""

import argon2

import sqlalchemy

from dds_web.database import models
from sqlalchemy.sql import func
from dds_web import exceptions
from flask import session


def verify_user_pass(username, password):
    """Verify that user exists and password is correct."""

    # Verify existing user
    try:
        user = models.User.query.filter(models.User.username == func.binary(username)).first()
    except sqlalchemy.exc.SQLAlchemyError:
        raise

    # User does not exist
    if not user:
        raise exceptions.AuthenticationError("Incorrect username and/or password!")

    # Verify password and generate token
    if verify_password_argon2id(user.password, password):
        # TODO (ina): Look into moving this (below)
        if "l" not in list(user.permissions):
            raise exceptions.AuthenticationError(
                f"The user '{username}' does not have any permissions"
            )

        # Password correct
        return True

    # Password incorrect
    return False


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


def validate_user_credentials(username, password):
    """Verifies if the given username and password is the match."""

    # TODO (ina): This is a version of the REST API authentication, both should use the same
    # base methods and call common functions where they are identical.
    # Check if user in db
    try:
        uaccount = models.User.query.filter(models.User.username == func.binary(username)).first()
    except SQLAlchemyError as e:
        print(str(e), flush=True)
        return (False, None, "Username not found (Credentials are case sensitive)", None)

    if not verify_password_argon2id(uaccount.password, password):
        return (False, None, "Incorrect password", None)

    uinfo = {"username": uaccount.username, "id": uaccount.id}
    if uaccount.role == "facility":
        try:
            facility_info = models.Facility.query.filter(
                models.Facility.id == func.binary(uaccount.facility_id)
            ).first()
        except SQLAlchemyError as e:
            return (False, None, "No facility found.", None)

        uinfo["facility_name"] = facility_info.name
        uinfo["facility_id"] = facility_info.id
    elif uaccount.role == "admin":
        uinfo["admin"] = True

    return (True, uaccount.role == "facility", "Validate successful", uinfo)
