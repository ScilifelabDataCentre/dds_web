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
import flask_wtf
import itsdangerous
import marshmallow
from jwcrypto import jwk, jwt
import pandas
import sqlalchemy
import wtforms
import wtforms.validators

# Own modules
from dds_web import auth
from dds_web.database import models
from dds_web.api.errors import JwtTokenGenerationError, DatabaseError, NoSuchInviteError
import dds_web.utils
from dds_web.api import marshmallows


####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def jwt_token(username):
    """Generates a JWT token."""
    expiration_time = datetime.datetime.utcnow() + datetime.timedelta(hours=48)
    data = {
        "sub": username,
        "exp": expiration_time.timestamp(),
    }
    key = jwk.JWK.from_password(flask.current_app.config.get("SECRET_KEY"))
    token = jwt.JWT(header={"alg": "HS256"}, claims=data, algs=["HS256"])
    token.make_signed_token(key)
    return token.serialize()


####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class AddUser(flask_restful.Resource):
    @auth.login_required
    def post(self):
        """Create an invite and send email."""

        try:
            # Use schema to validate and check args
            new_invite = marshmallows.InviteUserSchema().load(flask.request.args)

            # Add to database
            db.session.add(new_invite)
            db.session.commit()

        except marshmallow.ValidationError as valerr:
            flask.current_app.logger.info(valerr)
            return flask.jsonify(valerr.messages)
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise errors.DatabaseError(message=str(sqlerr))

        # Create URL safe token for invitation link
        s = itsdangerous.URLSafeTimedSerializer(flask.current_app.config["SECRET_KEY"])
        token = s.dumps(new_invite.email, salt="email-confirm")

        # Create link for invitation email
        link = flask.url_for("api_blueprint.confirm_invite", token=token, _external=True)

        # Compose and send email
        msg = flask_mail.Message("Confirm email", sender="localhost", recipients=[new_invite.email])
        msg.body = f"Your link is {link}"
        mail.send(msg)

        # TODO: Format response with marshal with?
        return flask.jsonify({"email": new_invite.email, "message": "Invite successful!"})


class ConfirmInvite(flask_restful.Resource):
    def get(self, token):
        """ """

        s = itsdangerous.URLSafeTimedSerializer(app.config.get("SECRET_KEY"))

        try:
            # Get email from token
            email = s.loads(token, salt="email-confirm", max_age=10000)

            # Get row from invite table
            invite_row = models.Invite.query.filter(models.Invite.email == email).first()

        except itsdangerous.exc.SignatureExpired:
            raise
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise DatabaseError(str(sqlerr))

        # Check the invite exists
        if not invite_row:
            raise NoSuchInviteError(email=email)

        # Get unit info from db
        facility_name = None
        if invite_row.is_facility:
            try:
                facility_info = (
                    models.Facility.query.filter(models.Facility.id == invite_row.facility_id)
                    .with_entities(models.Facility.name)
                    .first()
                )
            except sqlalchemy.exc.SQLAlchemyError as sqlerr:
                raise DatabaseError(str(sqlerr))

            # Raise exception if facility does not exist
            if not facility_info:
                raise DatabaseError(
                    message=f"User invite connected to a non-existent facility ID: {invite_row.facility_id}"
                )

            # Set facility name if exists
            facility_name = facility_info[0]

        # Initiate form
        form = dds_web.forms.RegistrationForm()

        # Prefill fields - facility readonly if filled, otherwise disabled
        form.facility_name.data = facility_name
        form.facility_name.render_kw = {"readonly": True} if facility_name else {"disabled": True}
        form.email.data = email
        form.username.data = email.split("@")[0]

        return flask.make_response(flask.render_template("user/register.html", form=form))


class NewUser(flask_restful.Resource):
    """Handles the creation of a new user"""

    def post(self):
        """Create user from form"""

        form = dds_web.forms.RegistrationForm()

        # Validate form - validators defined in form class
        if form.validate_on_submit():

            # Create new user row by loading form data into schema
            try:
                user_schema = marshmallows.NewUserSchema()
                new_user = user_schema.load(form.data)

            except marshmallow.ValidationError as valerr:
                app.logger.info(valerr)
                return flask.jsonify(valerr.messages)
            except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.IntegrityError) as sqlerr:
                raise DatabaseError(message=str("sqlerr"))

            return f"User added: {new_user}"

        return flask.make_response(flask.render_template("user/register.html", form=form))


class Token(flask_restful.Resource):
    """Generates token for the user."""

    @auth.login_required
    def get(self):
        return flask.jsonify({"token": jwt_token(username=auth.current_user().username)})


class ShowUsage(flask_restful.Resource):
    """Calculate and display the amount of GB hours and the total cost."""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
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
                    time_deleted = (
                        v.time_deleted if v.time_deleted else dds_web.utils.current_time()
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

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
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
