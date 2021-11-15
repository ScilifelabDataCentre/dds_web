"""User related endpoints e.g. authentication."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import datetime
import pathlib
import secrets
import os

# Installed
import flask
import flask_restful
import flask_mail
import itsdangerous
import marshmallow
from jwcrypto import jwk, jwt
import pandas
import sqlalchemy

# Own modules
from dds_web import auth, mail, db, basic_auth, limiter
from dds_web.database import models
import dds_web.utils
import dds_web.forms
import dds_web.api.errors as ddserr
from dds_web.api.schemas import project_schemas
from dds_web.api.schemas import user_schemas

# VARIABLES ############################################################################ VARIABLES #

ENCRYPTION_KEY_BIT_LENGTH = 256
ENCRYPTION_KEY_CHAR_LENGTH = int(ENCRYPTION_KEY_BIT_LENGTH / 8)

####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def rate_limit_from_config():
    return flask.current_app.config.get("TOKEN_ENDPOINT_ACCESS_LIMIT", "10/hour")


def encrypted_jwt_token(
    username, sensitive_content, expires_in=datetime.timedelta(hours=48), additional_claims=None
):
    """
    Encrypts a signed JWT token. This is to be used for any encrypted token regardless of the sensitive content.

    :param str username: Username must be obtained through authentication
    :param str or None sensitive_content: This is the content that must be protected by encryption.
        Can be set to None for protecting the signed token.
    :param timedelta expires_in: This is the maximum allowed age of the token. (default 2 days)
    :param Dict or None additional_claims: Any additional token claims can be added. e.g., {"iss": "DDS"}
    """
    token = jwt.JWT(
        header={"alg": "A256KW", "enc": "A256GCM"},
        claims=__signed_jwt_token(
            username=username,
            sensitive_content=sensitive_content,
            expires_in=expires_in,
            additional_claims=additional_claims,
        ),
    )
    key = jwk.JWK.from_password(flask.current_app.config.get("SECRET_KEY"))
    token.make_encrypted_token(key)
    return token.serialize()


def __signed_jwt_token(
    username,
    sensitive_content=None,
    expires_in=datetime.timedelta(hours=48),
    additional_claims=None,
):
    """
    Generic signed JWT token. This is to be used by both signed-only and signed-encrypted tokens.

    :param str username: Username must be obtained through authentication
    :param str or None sensitive_content: This is the content that must be protected by encryption. (default None)
    :param timedelta expires_in: This is the maximum allowed age of the token. (default 2 days)
    :param Dict or None additional_claims: Any additional token claims can be added. e.g., {"iss": "DDS"}
    """
    expiration_time = datetime.datetime.now() + expires_in
    data = {"sub": username, "exp": expiration_time.timestamp(), "nonce": secrets.token_hex(32)}
    if additional_claims is not None:
        data.update(additional_claims)
    if sensitive_content is not None:
        data["sen_con"] = sensitive_content

    key = jwk.JWK.from_password(flask.current_app.config.get("SECRET_KEY"))
    token = jwt.JWT(header={"alg": "HS256"}, claims=data, algs=["HS256"])
    token.make_signed_token(key)
    return token.serialize()


def jwt_token(username, expires_in=datetime.timedelta(hours=48), additional_claims=None):
    """
    Generates a signed JWT token. This is to be used for general purpose signed token.

    :param str username: Username must be obtained through authentication
    :param timedelta expires_in: This is the maximum allowed age of the token. (default 2 days)
    :param Dict or None additional_claims: Any additional token claims can be added. e.g., {"iss": "DDS"}
    """
    return __signed_jwt_token(
        username=username, expires_in=expires_in, additional_claims=additional_claims
    )


####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class AddUser(flask_restful.Resource):
    @auth.login_required
    def post(self):
        """Create an invite and send email."""

        args = flask.request.json

        project = ""
        if "project" in args:
            project = args.pop("project")

        # Check if email is registered to a user
        existing_user = user_schemas.UserSchema().load(args)

        if not existing_user:
            # Send invite if the user doesn't exist
            invite_user_result = self.invite_user(args)
            return flask.make_response(
                flask.jsonify(invite_user_result), invite_user_result["status"]
            )
        else:
            # If there is an existing user, add them to project.
            if project:
                add_user_result = self.add_user_to_project(existing_user, project, args.get("role"))
                flask.current_app.logger.debug(f"Add user result?: {add_user_result}")
                return flask.make_response(
                    flask.jsonify(add_user_result), add_user_result["status"]
                )
            else:
                return flask.make_response(
                    flask.jsonify(
                        {
                            "message": "User exists! Specify a project if you want to add this user to a project."
                        }
                    ),
                    ddserr.errors["DDSArgumentError"]["status"],
                )

    @staticmethod
    def invite_user(args):
        """Invite a new user"""

        try:
            # Use schema to validate and check args, and create invite row
            new_invite = user_schemas.InviteUserSchema().load(args)

        except ddserr.InviteError as invite_err:
            return {
                "message": invite_err.description,
                "status": ddserr.errors["InviteError"]["status"].value,
            }

        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise ddserr.DatabaseError(message=str(sqlerr))
        except marshmallow.ValidationError as valerr:
            raise ddserr.InviteError(message=valerr.messages)

        # Create URL safe token for invitation link
        s = itsdangerous.URLSafeTimedSerializer(flask.current_app.config["SECRET_KEY"])
        token = s.dumps(new_invite.email, salt="email-confirm")

        # Create link for invitation email
        link = flask.url_for("api_blueprint.confirm_invite", token=token, _external=True)

        # Compose and send email
        unit_name = None
        if auth.current_user().role in ["Unit Admin", "Unit Personnel"]:
            unit = auth.current_user().unit
            unit_name = unit.external_display_name
            unit_email = unit.contact_email
            sender_name = auth.current_user().name
            subject = f"{unit} invites you to the SciLifeLab Data Delivery System"
        else:
            sender_name = auth.current_user().name
            subject = f"{sender_name} invites you to the SciLifeLab Data Delivery System"

        msg = flask_mail.Message(
            subject,
            sender=flask.current_app.config["MAIL_SENDER_ADDRESS"],
            recipients=[new_invite.email],
        )

        # Need to attach the image to be able to use it
        msg.attach(
            "scilifelab_logo.png",
            "image/png",
            open(
                os.path.join(flask.current_app.static_folder, "img/scilifelab_logo.png"), "rb"
            ).read(),
            "inline",
            headers=[
                ["Content-ID", "<Logo>"],
            ],
        )

        msg.body = flask.render_template(
            "mail/invite.txt",
            link=link,
            sender_name=sender_name,
            unit_name=unit_name,
            unit_email=unit_email,
        )
        msg.html = flask.render_template(
            "mail/invite.html",
            link=link,
            sender_name=sender_name,
            unit_name=unit_name,
            unit_email=unit_email,
        )

        mail.send(msg)

        # TODO: Format response with marshal with?
        return {"email": new_invite.email, "message": "Invite successful!", "status": 200}

    @staticmethod
    def add_user_to_project(existing_user, project, role):
        """Add existing user to a project"""

        allowed_roles = ["Project Owner", "Researcher"]

        if role not in allowed_roles or existing_user.role not in allowed_roles:
            return {
                "status": 403,
                "message": "User Role should be either 'Project Owner' or 'Researcher' to be added to a project",
            }

        owner = False
        if role == "Project Owner":
            owner = True

        project = project_schemas.ProjectRequiredSchema().load({"project": project})
        ownership_change = False
        for rusers in project.researchusers:
            if rusers.researchuser is existing_user:
                if rusers.owner == owner:
                    return {
                        "status": 403,
                        "message": "User is already associated with the project in this capacity",
                    }

                ownership_change = True
                rusers.owner = owner
                break

        if not ownership_change:
            project.researchusers.append(
                models.ProjectUsers(
                    project_id=project.id,
                    user_id=existing_user.username,
                    owner=owner,
                )
            )

        try:
            db.session.commit()
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.IntegrityError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            message = "User was not associated with the project"
            raise ddserr.DatabaseError(message=f"Server Error: {message}")

        flask.current_app.logger.debug(
            f"User {existing_user.username} associated with project {project.public_id} as Owner={owner}."
        )

        return {
            "status": 200,
            "message": f"User {existing_user.username} associated with project {project.public_id} as Owner={owner}.",
        }


class ConfirmInvite(flask_restful.Resource):
    def get(self, token):
        """ """

        s = itsdangerous.URLSafeTimedSerializer(flask.current_app.config.get("SECRET_KEY"))

        try:
            # Get email from token
            email = s.loads(token, salt="email-confirm", max_age=604800)

            # Get row from invite table
            invite_row = models.Invite.query.filter(models.Invite.email == email).first()

        except itsdangerous.exc.SignatureExpired as signerr:
            db.session.delete(invite_row)
            db.session.commit()
            raise ddserr.InviteError(message=str(signerr))
        except itsdangerous.exc.BadSignature as badsignerr:
            raise ddserr.InviteError(message=str(badsignerr))
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise ddserr.DatabaseError(str(sqlerr))

        # Check the invite exists
        if not invite_row:
            raise ddserr.InviteError(
                message=f"There is no invitation for the found email adress: {email}"
            )

        # Initiate form
        form = dds_web.forms.RegistrationForm()

        # invite columns: unit_id, email, role
        flask.current_app.logger.debug(invite_row)

        # Prefill fields - facility readonly if filled, otherwise disabled
        form.unit_name.render_kw = {"disabled": True}
        if invite_row.unit:  # backref to unit
            form.unit_name.data = invite_row.unit.name
            form.unit_name.render_kw = {"readonly": True}

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
            flask.current_app.logger.debug(form.data)
            # Create new user row by loading form data into schema
            try:
                new_user = user_schemas.NewUserSchema().load(form.data)

            except marshmallow.ValidationError as valerr:
                flask.current_app.logger.info(valerr)
                raise
            except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.IntegrityError) as sqlerr:
                raise ddserr.DatabaseError(message=str(sqlerr))

            return f"User added: {new_user}"

        return flask.make_response(flask.render_template("user/register.html", form=form))


class Token(flask_restful.Resource):
    """Generates token for the user."""

    decorators = [
        limiter.limit(
            rate_limit_from_config,
            methods=["GET"],
            error_message=ddserr.errors["TooManyRequestsError"]["message"],
        )
    ]

    @basic_auth.login_required
    def get(self):
        return flask.jsonify({"token": jwt_token(username=auth.current_user().username)})


class EncryptedToken(flask_restful.Resource):
    """Generates encrypted token for the user."""

    decorators = [
        limiter.limit(
            rate_limit_from_config,
            methods=["GET"],
            error_message=ddserr.errors["TooManyRequestsError"]["message"],
        )
    ]

    @basic_auth.login_required
    def get(self):
        return flask.jsonify(
            {
                "token": encrypted_jwt_token(
                    username=auth.current_user().username, sensitive_content=None
                )
            }
        )


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
                models.Unit.id == sqlalchemy.func.binary(current_user.unit_id)
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
                models.Unit.id == sqlalchemy.func.binary(current_user.unit_id)
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
