"""Docstring"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import datetime
import pathlib

# Installed
from sqlalchemy.sql import func

# from flask import json
import flask
import flask_restful
import jwt
import pandas
import sqlalchemy

# Own modules
from dds_web import app, timestamp
from dds_web.database import models
from dds_web.api.dds_decorators import token_required
from dds_web.api.errors import MissingCredentialsError, DatabaseError, InvalidUserCredentialsError
from dds_web import exceptions
from dds_web.crypt import auth as dds_auth
from dds_web.api.errors import JwtTokenGenerationError

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


def jwt_token(username, project_id, project_access=False, permission="ls"):
    """Generates and encodes a JWT token."""

    try:
        token = jwt.encode(
            {
                "user": username,
                "project": {"id": project_id, "verified": project_access, "permission": permission},
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=48),
            },
            app.config["SECRET_KEY"],
        )
        app.logger.debug(f"token: {token}")
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


###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################


class AuthenticateUser(flask_restful.Resource):
    """Handles the authentication of the user."""

    def get(self):
        """Checks the username, password and generates the token."""

        # Get username and password from CLI request
        auth = flask.request.authorization
        if not auth or not auth.username or not auth.password:
            raise MissingCredentialsError

        # Project not required, will be checked for future operations
        args = flask.request.args
        project = args.get("project")

        # Verify username and password
        try:
            _ = dds_auth.verify_user_pass(username=auth.username, password=auth.password)

            # Generate jwt token
            token = jwt_token(username=auth.username, project_id=project)

        except (DatabaseError, InvalidUserCredentialsError, JwtTokenGenerationError):
            raise
        else:
            return flask.jsonify({"token": token.decode("UTF-8")})


class ShowUsage(flask_restful.Resource):
    """Calculate and display the amount of GB hours and the total cost."""

    method_decorators = [token_required]

    def get(self, current_user, _):

        # Check that user is facility account
        if current_user.role != "facility":
            flask.make_response(
                "Access denied - only facility accounts can get invoicing information.", 401
            )

        # Get facility info from table (incl safespring proj name)
        try:
            facility_info = models.Facility.query.filter(
                models.Facility.id == func.binary(current_user.facility_id)
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(f"Failed getting facility information: {err}", 500)

        # Total number of GB hours and cost saved in the db for the specific facility
        total_gbhours_db = 0.0
        total_cost_db = 0.0

        # Project (bucket) specific info
        usage = {}
        for p in facility_info.projects:

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
                        v.time_deleted if v.time_deleted else timestamp(),
                        "%Y-%m-%d %H:%M:%S.%f%z",
                    )
                    file_hours = (time_deleted - time_uploaded).seconds / (60 * 60)

                    # Calculate GBHours, if statement to avoid zerodivision exception
                    gb_hours = ((v.size_stored / 1e9) / file_hours) if file_hours else 0.0

                    # Save file version gbhours to project info and increase total facility sum
                    usage[p.public_id]["gbhours"] += gb_hours
                    total_gbhours_db += gb_hours

                    # Calculate approximate cost per gbhour: kr per gb per month / (days * hours)
                    cost_gbhour = 0.09 / (30 * 24)
                    cost = gb_hours * cost_gbhour

                    # Save file cost to project info and increase total facility cost
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

    method_decorators = [token_required]

    def get(self, current_user, _):

        # Check that user is facility account
        if current_user.role != "facility":
            flask.make_response(
                "Access denied - only facility accounts can get invoicing information.", 401
            )

        # Get facility info from table (incl safespring proj name)
        try:
            facility_info = models.Facility.query.filter(
                models.Facility.id == func.binary(current_user.facility_id)
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(f"Failed getting facility information: {err}", 500)

        # Get info from safespring invoice
        # TODO (ina): Move to another class or function - will be calling the safespring api
        csv_path = pathlib.Path("").parent / pathlib.Path("development/safespring_invoicespec.csv")
        csv_contents = pandas.read_csv(csv_path, sep=";", header=1)
        safespring_project_row = csv_contents.loc[
            csv_contents["project"] == facility_info.safespring
        ]

        app.logger.debug(safespring_project_row)

        return flask.jsonify({"test": "ok"})
