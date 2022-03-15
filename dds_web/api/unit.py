"""User related endpoints e.g. authentication."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import os
import smtplib
import time
import datetime

# Installed
import flask
import flask_restful
import flask_mail
import itsdangerous
import structlog
import sqlalchemy
import http


# Own modules
from dds_web import auth, mail, db, basic_auth, limiter
from dds_web.database import models
import dds_web.utils
import dds_web.forms
import dds_web.errors as ddserr
from dds_web.api.schemas import project_schemas, user_schemas, token_schemas
from dds_web.api.dds_decorators import (
    logging_bind_request,
    json_required,
    handle_validation_errors,
)
from dds_web.security.project_user_keys import (
    generate_invite_key_pair,
    share_project_private_key,
)
from dds_web.security.tokens import encrypted_jwt_token, update_token_with_mfa
from dds_web.security.auth import get_user_roles_common


# initiate bound logger
action_logger = structlog.getLogger("actions")

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class AllUnits(flask_restful.Resource):
    """Get unit info."""

    @auth.login_required(role=["Super Admin"])
    @logging_bind_request
    def get(self):
        """Return info about unit to super admin."""
        all_units = models.Unit.query.all()

        unit_info = [
            {
                "Name": u.name,
                "Public ID": u.public_id,
                "External Display Name": u.external_display_name,
                "Contact Email": u.contact_email,
                "Safespring Endpoint": u.safespring_endpoint,
                "Days In Available": u.days_in_available,
                "Days In Expired": u.days_in_expired,
            }
            for u in all_units
        ]

        return {
            "units": unit_info,
            "keys": [
                "Name",
                "Public ID",
                "External Display Name",
                "Days In Available",
                "Days In Expired",
                "Safespring Endpoint",
                "Contact Email",
            ],
        }
