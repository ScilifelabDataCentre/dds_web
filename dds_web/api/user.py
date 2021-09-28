"""User related endpoints e.g. authentication."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import datetime
import pathlib

# Installed
from sqlalchemy.sql import func

import flask
import flask_restful
import jwt
import pandas
import sqlalchemy

# Own modules
from dds_web import auth
from dds_web.database import models
from dds_web.api.errors import JwtTokenGenerationError
import dds_web.utils


####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def jwt_token(username):
    """Generates a JWT token."""

    try:
        token = jwt.encode(
            {
                "user": username,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=48),
            },
            flask.current_app.config.get("SECRET_KEY"),
            algorithm="HS256",
        )
        flask.current_app.logger.debug(f"token: {token}")
    except (
        TypeError,
        KeyError,
        jwt.exceptions.InvalidKeyError,
        jwt.exceptions.InvalidAlgorithmError,
        jwt.exceptions.MissingRequiredClaimError,
    ) as err:
        raise JwtTokenGenerationError(message=str(err))
    else:
        return token


####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class Token(flask_restful.Resource):
    """Generates token for the user."""

    @auth.login_required
    def get(self):
        return flask.jsonify({"token": jwt_token(username=auth.current_user().username)})


class ShowUsage(flask_restful.Resource):
    """Calculate and display the amount of GB hours and the total cost."""

    @auth.login_required
    def get(self):
        current_user = auth.current_user()

        # Check that user is unit account
        if current_user.role != "unit":
            flask.make_response(
                "Access denied - only unit accounts can get invoicing information.", 401
            )

        # Get unit info from table (incl safespring proj name)
        try:
            unit_info = models.Unit.query.filter(
                models.Unit.id == func.binary(current_user.unit_id)
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            flask.current_app.logger.exception(err)
            return flask.make_response(f"Failed getting unit information.", 500)

        # Total number of GB hours and cost saved in the db for the specific unit
        total_gbhours_db = 0.0
        total_cost_db = 0.0

        # Project (bucket) specific info
        usage = {}
        for p in unit_info.projects:

            # Define fields in usage dict
            usage[p.public_id] = {"gbhours": 0.0, "cost": 0.0}

            for f in p.files:
                for v in f.versions:
                    # Calculate hours of the current file
                    time_uploaded = datetime.datetime.strptime(
                        v.time_uploaded,
                        "%Y-%m-%d %H:%M:%S.%f%z",
                    )
                    time_deleted = datetime.datetime.strptime(
                        v.time_deleted if v.time_deleted else dds_web.utils.timestamp(),
                        "%Y-%m-%d %H:%M:%S.%f%z",
                    )
                    file_hours = (time_deleted - time_uploaded).seconds / (60 * 60)

                    # Calculate GBHours, if statement to avoid zerodivision exception
                    gb_hours = ((v.size_stored / 1e9) / file_hours) if file_hours else 0.0

                    # Save file version gbhours to project info and increase total unit sum
                    usage[p.public_id]["gbhours"] += gb_hours
                    total_gbhours_db += gb_hours

                    # Calculate approximate cost per gbhour: kr per gb per month / (days * hours)
                    cost_gbhour = 0.09 / (30 * 24)
                    cost = gb_hours * cost_gbhour

                    # Save file cost to project info and increase total unit cost
                    usage[p.public_id]["cost"] += cost
                    total_cost_db += cost

            usage[p.public_id].update(
                {
                    "gbhours": round(usage[p.public_id]["gbhours"], 2),
                    "cost": round(usage[p.public_id]["cost"], 2),
                }
            )

        return flask.jsonify(
            {
                "total_usage": {
                    "gbhours": round(total_gbhours_db, 2),
                    "cost": round(total_cost_db, 2),
                },
                "project_usage": usage,
            }
        )


class InvoiceUnit(flask_restful.Resource):
    """Calculate the actual cost from the Safespring invoicing specification."""

    @auth.login_required
    def get(self):
        current_user = auth.current_user()

        # Check that user is unit account
        if current_user.role != "unit":
            flask.make_response(
                "Access denied - only unit accounts can get invoicing information.", 401
            )

        # Get unit info from table (incl safespring proj name)
        try:
            unit_info = models.Unit.query.filter(
                models.Unit.id == func.binary(current_user.unit_id)
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            flask.current_app.logger.exception(err)
            return flask.make_response(f"Failed getting unit information.", 500)

        # Get info from safespring invoice
        # TODO (ina): Move to another class or function - will be calling the safespring api
        csv_path = pathlib.Path("").parent / pathlib.Path("development/safespring_invoicespec.csv")
        csv_contents = pandas.read_csv(csv_path, sep=";", header=1)
        safespring_project_row = csv_contents.loc[csv_contents["project"] == unit_info.safespring]

        flask.current_app.logger.debug(safespring_project_row)

        return flask.jsonify({"test": "ok"})
