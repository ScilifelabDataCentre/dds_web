"""Functions related to the login/access process.

Used by endpoints for access checks.
"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import os
import argon2
import datetime
from cryptography.hazmat.primitives.kdf import scrypt
import cryptography.hazmat.backends as backends
import sqlalchemy

# Own modules
from code_dds import C_TZ
from code_dds import db, timestamp, token_expiration
from code_dds.db_code import models
from code_dds.db_code import db_utils


###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################

# def cloud_access(project):
#     """Gets the S3 project ID (bucket ID).

#     Args:
#         project:    Specified project ID used in current delivery

#     Returns:
#         tuple:  access, s3 project ID and error message
#     """

#     # Get s3 info if project in database
#     s3_info = S3Project.query.filter_by(project_id=project).first()

#     # Return error if s3 info not found
#     if s3_info is None:
#         return False, "", "There is no recorded S3 project for the " + \
#             "specified project"

#     # Access granted, S3 ID and no error message
#     return True, s3_info.id, ""


def ds_access(username, password, role) -> (bool, int, str):
    """Finds facility in db and validates the password given by user.

    Args:
        username:   The users username
        password:   The users password

    Returns:
        tuple:  If access to DS granted, facility/user ID and error message

    """

    if role == "facility":
        table = models.Facility
    elif role == "user":
        table = models.User
    else:
        pass  # TODO (ina/senthil) : cancel/custom error here?

    # Get user from database
    try:
        user = (
            table.query.filter_by(username=username).with_entities(table.id, table.password).first()
        )
    except sqlalchemy.exc.SQLAlchemyError as e:
        print(str(e), flush=True)

    # Return error if username doesn't exist in database
    if user is None:
        return False, 0, "The user does not exist"

    # Return error if the password doesn't match
    if not verify_password(user[1], password):
        return False, 0, "Incorrect password!"

    return True, user[0], ""


def project_access(uid, project, owner, role="facility") -> (bool, str):
    """Checks the users access to the specified project

    Args:
        id:     Facility ID
        project:    Project ID
        owner:      Owner ID

    Returns:
        tuple:  access and error message
    """

    if role == "facility":
        # Get project info if owner and facility matches
        project_info = (
            models.Project.query.filter_by(id=project, owner=owner, facility=uid)
            .with_entities(models.Project.delivery_option, models.Project.public_key)
            .first()
        )
    else:
        # Get project info if owner matches
        # TODO (ina): possibly another check here
        project_info = (
            models.Project.query.filter_by(id=project, owner=owner)
            .with_entities(models.Project.delivery_option, models.Project.public_key)
            .first()
        )

    # Return error if project not found
    if project_info is None:
        return False, None, "The project doesn't exist or you don't have access"

    # Return error if project doesn't have access to S3
    if project_info[0] != "S3":
        return False, None, "The project does not have S3 access"

    # Check length of public key and quit if wrong
    # ---- here ----

    return True, project_info[1], ""


def verify_password(db_pw, input_pw):
    password_hasher = argon2.PasswordHasher()
    try:
        password_hasher.verify(db_pw, input_pw)
    except (
        argon2.exceptions.VerifyMismatchError,
        argon2.exceptions.VerificationError,
        argon2.exceptions.InvalidHash,
    ) as err:
        print(err, flush=True)
        return False
    return True


# def secure_password_hash(password_settings: str,
#                          password_entered: str) -> (str):
#     """Generates secure password hash.
#
#     Args:
#             password_settings:  String containing the salt, length of hash,
#                                 n-exponential, r and p variables.
#                                 Taken from database. Separated by '$'.
#             password_entered:   The user-specified password.
#
#     Returns:
#             str:    The derived hash from the user-specified password.
#
#     """
#
#     # Split scrypt settings into parts
#     settings = password_settings.split("$")
#     for i in [1, 2, 3, 4]:
#         settings[i] = int(settings[i])  # Set settings as int, not str
#
#     # Create cryptographically secure password hash
#     kdf = scrypt.Scrypt(salt=bytes.fromhex(settings[0]),
#                         length=settings[1],
#                         n=2**settings[2],
#                         r=settings[3],
#                         p=settings[4],
#                         backend=backends.default_backend())
#
#     return (kdf.derive(password_entered.encode("utf-8"))).hex()


def gen_access_token(project, length: int = 16) -> (str):
    """Generate access token for logged in user and save to database.

    Args:
        project:    Project ID
        length:     Length of token

    Returns:
        str:    Token
    """

    # Generate random bytes as token and make hex string
    token = os.urandom(length).hex()

    # Check if token exists in token db and generate new token until not in db
    curr_token = models.Tokens.query.filter_by(token=token).first()
    while curr_token is not None:
        token = os.urandom(length).hex()
        curr_token = models.Tokens.query.filter_by(token=token).first()

    # Create new token object for db and add it
    new_token = models.Tokens(
        token=token, project_id=project, created=timestamp(), expires=token_expiration()
    )
    db.session.add(new_token)
    db.session.commit()

    return token


def validate_token(token: str, project_id):
    """Checks that the token specified in the request is valid.

    Args:
        token (str):    The request token

    Returns:
        bool:   True if token validated
    """

    validated = False  # Returned variable - changes is validated

    # Get token from db matching the specified token in request
    try:
        token_info = models.Tokens.query.filter_by(token=token, project_id=project_id).first()
    except sqlalchemy.exc.SQLAlchemyError as e:
        print(e, flush=True)
        return validated

    # Access to project delivery not granted if the token is not in db
    if token_info is None:
        return validated

    # Transform timestamps in db to datetime object
    try:
        date_time_created = datetime.datetime.strptime(token_info.created, "%Y-%m-%d %H:%M:%S.%f%z")
        date_time_expires = datetime.datetime.strptime(token_info.expires, "%Y-%m-%d %H:%M:%S.%f%z")
    except ValueError as e:
        print(e, flush=True)
        return validated

    # Get current time and check if it is within correct interval
    now = datetime.datetime.now(tz=C_TZ)
    if date_time_created < now < date_time_expires:
        validated = True

    return validated
