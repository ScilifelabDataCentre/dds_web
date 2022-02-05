"""User related endpoints e.g. authentication."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import datetime
import logging
import pathlib
import secrets
import os
import smtplib
import time

# Installed
import flask
import flask_restful
import flask_mail
import itsdangerous
import marshmallow
import structlog
import sqlalchemy
import http


# Own modules
from dds_web import auth, mail, db, basic_auth, limiter
from dds_web.database import models
import dds_web.utils
import dds_web.forms
import dds_web.errors as ddserr
from dds_web.api.db_connector import DBConnector
from dds_web.api.schemas import project_schemas, user_schemas, token_schemas
from dds_web.api.dds_decorators import logging_bind_request
from dds_web.security.tokens import encrypted_jwt_token, update_token_with_mfa

# initiate bound logger
action_logger = structlog.getLogger("actions")


####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################
class AddUser(flask_restful.Resource):
    @auth.login_required
    @logging_bind_request
    def post(self):
        """Create an invite and send email."""

        project = flask.request.args.get("project", None)
        args = flask.request.json
        # Check if email is registered to a user
        existing_user = user_schemas.UserSchema().load(args)

        if existing_user and not project:
            raise ddserr.DDSArgumentError(
                message="User exists! Specify a project if you want to add this user to a project."
            )

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

    @staticmethod
    @logging_bind_request
    def invite_user(args):
        """Invite a new user"""

        try:
            # Use schema to validate and check args, and create invite row
            new_invite = user_schemas.InviteUserSchema().load(args)

        except ddserr.InviteError as invite_err:
            return {
                "message": invite_err.description,
                "status": ddserr.InviteError.code.value,
            }

        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise ddserr.DatabaseError(message=str(sqlerr))
        except marshmallow.ValidationError as valerr:
            raise ddserr.InviteError(message=valerr.messages)

        # Create URL safe token for invitation link
        s = itsdangerous.URLSafeTimedSerializer(flask.current_app.config["SECRET_KEY"])
        token = s.dumps(new_invite.email, salt="email-confirm")

        # Create link for invitation email
        link = flask.url_for("auth_blueprint.confirm_invite", token=token, _external=True)

        # Compose and send email
        unit_name = None
        if auth.current_user().role in ["Unit Admin", "Unit Personnel"]:
            unit = auth.current_user().unit
            unit_name = unit.external_display_name
            unit_email = unit.contact_email
            sender_name = auth.current_user().name
            subject = f"{unit_name} invites you to the SciLifeLab Data Delivery System"
        else:
            sender_name = auth.current_user().name
            subject = f"{sender_name} invites you to the SciLifeLab Data Delivery System"

        msg = flask_mail.Message(
            subject,
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

        AddUser.send_email_with_retry(msg)

        # Append invite to unit if applicable
        if new_invite.role in ["Unit Admin", "Unit Personnel"]:
            auth.current_user().unit.invites.append(new_invite)
        else:
            db.session.add(new_invite)

        db.session.commit()

        # TODO: Format response with marshal with?
        return {"email": new_invite.email, "message": "Invite successful!", "status": 200}

    @staticmethod
    def send_email_with_retry(msg, times_retried=0):
        """Send email with retry on exception"""

        try:
            mail.send(msg)
        except smtplib.SMTPException as err:
            # Wait a little bit
            time.sleep(10)
            # Retry twice
            if times_retried < 2:
                retry = times_retried + 1
                AddUser.send_email_with_retry(msg, retry)

    @staticmethod
    @logging_bind_request
    def add_user_to_project(existing_user, project, role):
        """Add existing user to a project"""

        allowed_roles = ["Project Owner", "Researcher"]

        if role not in allowed_roles or existing_user.role not in allowed_roles:
            return {
                "status": ddserr.AccessDeniedError.code.value,
                "message": (
                    "User Role should be either 'Project Owner' or "
                    "'Researcher' to be added to a project"
                ),
            }

        owner = role == "Project Owner"

        project = project_schemas.ProjectRequiredSchema().load({"project": project})
        ownership_change = False
        for rusers in project.researchusers:
            if rusers.researchuser is existing_user:
                if rusers.owner == owner:
                    return {
                        "status": ddserr.RoleException.code.value,
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
            "status": http.HTTPStatus.OK,
            "message": f"User {existing_user.username} associated with project {project.public_id} as Owner={owner}.",
        }


class RetrieveUserInfo(flask_restful.Resource):
    @auth.login_required
    @logging_bind_request
    def get(self):
        """Return own info when queried"""
        curr_user = auth.current_user()
        info = {}
        info["email_primary"] = curr_user.primary_email
        info["emails_all"] = [x.email for x in curr_user.emails]
        info["role"] = curr_user.role
        info["username"] = curr_user.username
        info["name"] = curr_user.name
        if "Unit" in curr_user.role and curr_user.is_admin:
            info["is_admin"] = curr_user.is_admin
        return {"info": info}


class DeleteUserSelf(flask_restful.Resource):
    """Endpoint to initiate user self removal from the system
    Every user can self-delete the own account with an e-mail confirmation.
    """

    @auth.login_required
    @logging_bind_request
    def delete(self):

        current_user = auth.current_user()

        email_str = current_user.primary_email

        username = current_user.username

        proj_ids = [proj.public_id for proj in current_user.projects]

        # Create URL safe token for invitation link
        s = itsdangerous.URLSafeTimedSerializer(flask.current_app.config["SECRET_KEY"])
        token = s.dumps(email_str, salt="email-delete")

        # Create deletion request in database unless it already exists
        try:
            if not dds_web.utils.delrequest_exists(email_str):
                new_delrequest = models.DeletionRequest(
                    **{
                        "requester": current_user,
                        "email": email_str,
                        "issued": dds_web.utils.current_time(),
                    }
                )
                db.session.add(new_delrequest)
                db.session.commit()
            else:
                return {
                    "message": f"The confirmation link has already been sent to your address {email_str}!",
                    "status": 200,
                }

        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            db.session.rollback()
            raise ddserr.DatabaseError(
                message=f"Creation of self-deletion request failed due to database error: {sqlerr}",
                pass_message=False,
            )

        # Create link for deletion request email
        link = flask.url_for("auth_blueprint.confirm_self_deletion", token=token, _external=True)
        subject = f"Confirm deletion of your user account {username} in the SciLifeLab Data Delivery System"
        projectnames = "; ".join(proj_ids)

        msg = flask_mail.Message(
            subject,
            recipients=[email_str],
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
            "mail/deletion_request.txt",
            link=link,
            sender_name=current_user.name,
            projects=projectnames,
        )
        msg.html = flask.render_template(
            "mail/deletion_request.html",
            link=link,
            sender_name=current_user.name,
            projects=projectnames,
        )

        mail.send(msg)

        flask.current_app.logger.info(
            f"The user account {username} / {email_str} ({current_user.role}) has requested self-deletion."
        )

        return flask.make_response(
            flask.jsonify(
                {
                    "message": f"Requested account deletion initiated. An e-mail with a confirmation link has been sent to your address {email_str}!",
                }
            )
        )


class UserActivation(flask_restful.Resource):
    """Endpoint to reactivate/deactivate users in the system

    Unit admins can reactivate/deactivate unitusers. Super admins can reactivate/deactivate any user."""

    @auth.login_required(role=["Super Admin", "Unit Admin"])
    @logging_bind_request
    def post(self):
        user = user_schemas.UserSchema().load(flask.request.json)
        action = flask.request.json.get("action")
        if action is None or action == "":
            raise ddserr.DDSArgumentError(
                message=f"Please provide an action 'deactivate' or 'reactivate' for this request."
            )
        if user is None:
            raise ddserr.NoSuchUserError(
                message=f"This e-mail address is not associated with a user in the DDS, make sure it is not misspelled."
            )
        user_email_str = user.primary_email
        current_user = auth.current_user()

        if current_user.role == "Unit Admin":
            if user.role not in ["Unit Admin", "Unit Personnel"] or current_user.unit != user.unit:
                raise ddserr.AccessDeniedError(
                    message=f"You are not allowed to {action} this user. As a unit admin, you're only allowed to {action} users in your unit."
                )

        if current_user == user:
            raise ddserr.AccessDeniedError(message=f"You cannot {action} your own account!")

        if (action == "reactivate" and user.is_active) or (
            action == "deactivate" and not user.is_active
        ):
            raise ddserr.DDSArgumentError(message=f"User is already in desired state!")

        # TODO: Check if user has lost access to any projects and if so, grant access again.
        try:
            user.active = action == "reactivate"
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            raise DatabaseError(message=str(err))
        msg = f"The user account {user.username} ({user_email_str}, {user.role})  has been {action}d successfully been by {current_user.name} ({current_user.role})."
        flask.current_app.logger.info(msg)

        with structlog.threadlocal.bound_threadlocal(
            who={"user": user.username, "role": user.role},
            by_whom={"user": current_user.username, "role": current_user.role},
        ):
            action_logger.info(self.__class__)

        return flask.make_response(
            flask.jsonify(
                {
                    "message": f"You successfully {action}d the account {user.username} ({user_email_str}, {user.role})!"
                }
            )
        )


class DeleteUser(flask_restful.Resource):
    """Endpoint to remove users from the system

    Unit admins can delete unitusers. Super admins can delete any user."""

    @auth.login_required(role=["Super Admin", "Unit Admin"])
    @logging_bind_request
    def delete(self):

        user = user_schemas.UserSchema().load(flask.request.json)
        if not user:
            raise ddserr.UserDeletionError(
                message=(
                    f"This e-mail address is not associated with a user in the DDS, "
                    "make sure it is not misspelled."
                )
            )

        user_email_str = user.primary_email
        current_user = auth.current_user()

        if current_user.role == "Unit Admin":
            if user.role not in ["Unit Admin", "Unit Personnel"] or current_user.unit != user.unit:
                raise ddserr.UserDeletionError(
                    message=f"You are not allowed to delete this user. As a unit admin, you're only allowed to delete users in your unit."
                )

        if current_user == user:
            raise ddserr.UserDeletionError(
                message=f"To delete your own account, use the '--self' flag instead!"
            )

        DBConnector().delete_user(user)

        msg = f"The user account {user.username} ({user_email_str}, {user.role})  has been terminated successfully been by {current_user.name} ({current_user.role})."
        flask.current_app.logger.info(msg)

        with structlog.threadlocal.bound_threadlocal(
            who={"user": user.username, "role": user.role},
            by_whom={"user": current_user.username, "role": current_user.role},
        ):
            action_logger.info(self.__class__)

        return flask.make_response(
            flask.jsonify(
                {
                    "message": f"You successfully deleted the account {user.username} ({user_email_str}, {user.role})!"
                }
            )
        )


class RemoveUserAssociation(flask_restful.Resource):
    @auth.login_required
    @logging_bind_request
    def post(self):
        """Remove a user from a project"""

        project_id = flask.request.args.get("project")

        args = flask.request.json
        user_email = args.pop("email")

        # Check if email is registered to a user
        existing_user = user_schemas.UserSchema().load({"email": user_email})
        project = project_schemas.ProjectRequiredSchema().load({"project": project_id})

        if existing_user:
            user_in_project = False
            for user_association in project.researchusers:
                if user_association.user_id == existing_user.username:
                    user_in_project = True
                    db.session.delete(user_association)
            if user_in_project:
                try:
                    db.session.commit()
                    message = (
                        f"User with email {user_email} no longer associated with {project_id}."
                    )
                except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.IntegrityError) as err:
                    flask.current_app.logger.exception(err)
                    db.session.rollback()
                    message = "Removing user association with the project has not succeeded"
                    raise ddserr.DatabaseError(message=f"Server Error: {message}")
            else:
                message = "User already not associated with this project"
            status = 200
            flask.current_app.logger.debug(
                f"User {existing_user.username} no longer associated with project {project.public_id}."
            )
        else:
            message = f"{user_email} already not associated with this project"
            status = NoSuchUserError.code.value

        return {"message": message}, status


class EncryptedToken(flask_restful.Resource):
    """Generates encrypted token for the user."""

    decorators = [
        limiter.limit(
            dds_web.utils.rate_limit_from_config,
            methods=["GET"],
            error_message=ddserr.TooManyRequestsError.description,
        )
    ]

    @basic_auth.login_required
    @logging_bind_request
    def get(self):
        return flask.jsonify(
            {
                "message": "Please take this token to /user/second_factor to authenticate with MFA!",
                "token": encrypted_jwt_token(
                    username=auth.current_user().username, sensitive_content=None
                ),
            }
        )


class SecondFactor(flask_restful.Resource):
    """Take in and verify an authentication one-time code entered by an authenticated user with basic credentials"""

    @auth.login_required
    def get(self):
        args = flask.request.json
        if args is None:
            args = {}

        token_schemas.TokenSchema().load(args)

        token_claims = dds_web.security.auth.decrypt_and_verify_token_signature(
            flask.request.headers["Authorization"].split()[1]
        )

        return flask.jsonify({"token": update_token_with_mfa(token_claims)})


class ShowUsage(flask_restful.Resource):
    """Calculate and display the amount of GB hours and the total cost."""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    def get(self):
        current_user = auth.current_user()

        # Check that user is unit account
        if current_user.role != "unit":
            raise ddserr.AccessDeniedError(
                "Access denied - only unit accounts can get invoicing information."
            )

        # Get unit info from table (incl safespring proj name)
        try:
            unit_info = models.Unit.query.filter(
                models.Unit.id == sqlalchemy.func.binary(current_user.unit_id)
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            flask.current_app.logger.exception(err)
            raise ddserr.DatabaseError(f"Failed getting unit information.")

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
                    time_uploaded = v.time_uploaded
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
