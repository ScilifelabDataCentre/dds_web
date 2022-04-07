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
