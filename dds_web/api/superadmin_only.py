"""User related endpoints e.g. authentication."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library

# Installed
import flask_restful
import flask
import structlog

# Own modules
from dds_web import auth, db
from dds_web.database import models
from dds_web.api.dds_decorators import json_required, logging_bind_request, handle_db_error
from dds_web import utils
import dds_web.errors as ddserr


# initiate bound logger
action_logger = structlog.getLogger("actions")

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class AllUnits(flask_restful.Resource):
    """Get unit info."""

    @auth.login_required(role=["Super Admin"])
    @logging_bind_request
    @handle_db_error
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


class MOTD(flask_restful.Resource):
    """Add a new MOTD message."""

    @auth.login_required(role=["Super Admin"])
    @logging_bind_request
    @json_required
    @handle_db_error
    def post(self):
        """Add a MOTD."""

        curr_date = utils.current_time()
        json_input = flask.request.json
        motd = json_input.get("message")
        if not motd:
            raise ddserr.DDSArgumentError(message="No MOTD specified.")

        flask.current_app.logger.debug(motd)
        new_motd = models.MOTD(message=motd, date_created=curr_date)
        db.session.add(new_motd)
        db.session.commit()

        return {"message": "The MOTD was successfully added to the database."}

    @handle_db_error
    def get(self):
        """Get the latest MOTD from database."""
        motd = utils.get_latest_motd()
        return {"message": motd}


class AllUsers(flask_restful.Resource):
    """Get all users or check if there a specific user in the database."""

    @auth.login_required(role=["Super Admin"])
    @logging_bind_request
    @handle_db_error
    def get(self):
        """Return users or a confirmation on if one exists."""
        json_input = flask.request.json
        if json_input:
            user_to_find = json_input.get("username")
            if not user_to_find:
                raise ddserr.DDSArgumentError(
                        message="Username required to check existence of account."
                    )
                          
            return {
                "exists": models.User.query.filter_by(username=user_to_find).one_or_none()
                is not None
            }

        keys = ["Name", "Username", "Email", "Role", "Active"]

        users = [
            {
                "Name": user.name,
                "Username": user.username,
                "Email": user.primary_email,
                "Role": user.role,
                "Active": user.is_active,
            }
            for user in models.User.query.all()
        ]

        return {"users": users, "keys": keys, "empty": not users}
