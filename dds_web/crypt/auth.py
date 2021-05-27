"""Password related cryptography stuff"""

import argon2

from sqlalchemy.exc import SQLAlchemyError

from dds_web.database import models
from sqlalchemy.sql import func


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

    # get type of the user
    # try:
    #     user_role = models.Role.query.filter(models.Role.username == func.binary(username)).first()
    # except SQLAlchemyError as e:
    #     print(str(e), flush=True)

    # Exit if user not exisit in Roles table

    # if user_role is None:
    #     return (False, None, "User doesn't exist (Credentials are case sensitive)", None)
    # is_facility = user_role.facility == 1
    # table = models.Facility if is_facility else models.User

    try:
        uaccount = models.User.query.filter(models.User.username == func.binary(username)).first()
    except SQLAlchemyError as e:
        print(str(e), flush=True)
        return (False, None, "Username not found (Credentials are case sensitive)", None)

    if not verify_password_argon2id(uaccount.password, password):
        return (False, None, "Incorrect password", None)

    uinfo = {"username": uaccount.username, "id": uaccount.public_id}
    if uaccount.role == "facility":
        try:
            facility_info = models.Facility.query.filter(
                models.Facility.public_id == func.binary(uaccount.facility_id)
            ).first()
        except SQLAlchemyError as e:
            return (False, None, "No facility found.", None)

        uinfo["facility_name"] = facility_info.name
    elif uaccount.role == "admin":
        uinfo["admin"] = True

    return (True, uaccount.role == "facility", "Validate successful", uinfo)
