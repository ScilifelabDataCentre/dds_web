"""Docstring"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import datetime
import binascii
import pathlib

# Installed
import flask
import flask_restful
import jwt
import sqlalchemy
import functools
from sqlalchemy.sql import func
import pandas

# Own modules
from dds_web import app, timestamp
from dds_web.database import models
from dds_web.crypt.auth import gen_argon2hash, verify_password_argon2id
from dds_web.api.dds_decorators import token_required

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


def jwt_token(username, project_id, project_access=False, permission="ls"):
    """Generates and encodes a JWT token."""

    token, error = (None, "")
    try:
        token = jwt.encode(
            {
                "user": username,
                "project": {"id": project_id, "verified": project_access, "permission": permission},
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=48),
            },
            app.config["SECRET_KEY"],
        )
    except Exception as err:
        token, error = (None, str(err))

    return token, error


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
            return flask.make_response("Could not verify", 401)

        # Project not required, will be checked for future operations
        args = flask.request.args
        if "project" not in args:
            project = None
        else:
            project = args["project"]

        # Check if user in db
        try:
            user = models.User.query.filter(
                models.User.username == func.binary(auth.username)
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            return flask.make_response(f"Database connection failed: {sqlerr}", 500)

        if not user:
            return flask.make_response(
                f"User not found in system. User access denied: '{auth.username}'", 401
            )

        # Verify user password and generate token
        if verify_password_argon2id(user.password, auth.password):
            if "l" not in list(user.permissions):
                return flask.make_response(
                    f"The user '{auth.username}' does not have any permissions", 401
                )

            token, error = jwt_token(username=user.username, project_id=project)
            if token is None:
                return flask.make_response(error, 500)

            # Success - return token
            app.logger.debug("Token generated. Returning to CLI.")
            return flask.jsonify({"token": token.decode("UTF-8")})

        # Failed - incorrect password
        return flask.make_response("Incorrect password!", 401)


class ShowUsage(flask_restful.Resource):
    """Calculate and display the amount of GB hours and the total cost."""

    method_decorators = [token_required]

    def get(self, current_user, _):

        # Check that user is facility account
        if current_user.role != "facility":
            flask.make_response(
                "Access denied - only facility accounts can get invoicing information.", 401
            )

        # Get safespring project name from facility table
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

        # Total GBHours for safespring project
        # total_gbhours_sfsp = safespring_project_row.units.values[0]

        # Total number of GB hours saved in the db for the specific facility
        total_gbhours_db = 0.0

        # Calculate the GBHours for each project
        try:

            # Project (bucket) specific info
            usage = {}
            for p in facility_info.projects:

                usage[p.public_id] = {"gbhours": 0.0, "cost": 0.0, "gbh_perc": 0.0}
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

                        # Calculate GBHours
                        gb_hours = ((v.size_stored / 1e9) / file_hours) if file_hours else 0.0

                        # Add to project sum and increase total
                        usage[p.public_id]["gbhours"] += gb_hours
                        total_gbhours_db += gb_hours

            for p in usage:
                # GBHour percentage of total in database for facility
                proj_gbhour_percentage = (
                    (usage[p]["gbhours"] / total_gbhours_db) if total_gbhours_db else 0.0
                )

                usage[p].update(
                    {
                        "gbhours": str(usage[p]["gbhours"]),
                        "gbh_perc": str(proj_gbhour_percentage),
                        "cost": str(
                            safespring_project_row.subtotal.values[0] * proj_gbhour_percentage
                        ),
                    }
                )

        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response("Failed getting project files: {err}", 500)

        app.logger.debug(usage)

        return flask.jsonify(
            {
                "total_usage": str(total_gbhours_db),
                "total_cost": str(safespring_project_row.subtotal.values[0]),
                "project_usage": usage,
            }
        )
