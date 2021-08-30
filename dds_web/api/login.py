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
from dds_web import C_TZ
from dds_web import db, timestamp, token_expiration
from dds_web.database import models
from dds_web.database import db_utils


###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################

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

