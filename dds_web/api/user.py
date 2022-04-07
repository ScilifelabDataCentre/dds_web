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
    handle_db_error,
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
class AddUser(flask_restful.Resource):
    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel", "Project Owner"])
    @logging_bind_request
    @json_required
    @handle_validation_errors
    def post(self):
        """Associate existing users or unanswered invites with projects or create invites"""
        args = flask.request.args
        json_info = flask.request.json

        # Verify valid role (should also catch None)
        role = json_info.get("role")
        if not dds_web.utils.valid_user_role(specified_role=role):
            raise ddserr.DDSArgumentError(message="Invalid user role.")

        # Unit only changable for Super Admin invites
        unit = json_info.get("unit") if auth.current_user().role == "Super Admin" else None

        # A project may or may not be specified
        project = args.get("project") if args else None
        if project:
            project = project_schemas.ProjectRequiredSchema().load({"project": project})

        # Verify email
        email = json_info.get("email")
        if not email:
            raise ddserr.DDSArgumentError(message="Email address required to add or invite.")

        # Notify the users about project additions? Invites are still being sent out.
        send_email = json_info.get("send_email", True)

        # Check if email is registered to a user
        try:
            existing_user = user_schemas.UserSchema().load({"email": email})
            unanswered_invite = user_schemas.UnansweredInvite().load({"email": email})
        except sqlalchemy.exc.OperationalError as err:
            raise ddserr.DatabaseError(message=str(err), alt_message="Unexpected database error.")

        if existing_user or unanswered_invite:
            if not project:
                raise ddserr.DDSArgumentError(
                    message=(
                        "This user was already added to the system. "
                        "Specify the project you wish to give access to."
                    )
                )

            add_user_result = self.add_to_project(
                whom=existing_user or unanswered_invite,
                project=project,
                role=role,
                send_email=send_email,
            )
            return add_user_result, add_user_result["status"]

        else:
            # Send invite if the user doesn't exist
            invite_user_result = self.invite_user(
                email=email, new_user_role=role, project=project, unit=unit
            )

            return invite_user_result, invite_user_result["status"]

    @staticmethod
    @logging_bind_request
    def invite_user(email, new_user_role, project=None, unit=None):
        """Invite a new user"""

        current_user_role = get_user_roles_common(user=auth.current_user())

        if not project:
            if current_user_role == "Project Owner":
                return {
                    "status": ddserr.InviteError.code.value,
                    "message": "Project ID required to invite users to projects.",
                }
            if new_user_role == "Project Owner":
                return {
                    "status": ddserr.InviteError.code.value,
                    "message": "Project ID required to invite a 'Project Owner'.",
                }

        # Verify role or current and new user
        if current_user_role == "Super Admin" and project:
            return {
                "status": ddserr.InviteError.code.value,
                "message": (
                    "Super Admins do not have project data access and can therefore "
                    "not invite users to specific projects."
                ),
            }
        elif current_user_role == "Unit Admin" and new_user_role == "Super Admin":
            return {
                "status": ddserr.AccessDeniedError.code.value,
                "message": ddserr.AccessDeniedError.description,
            }
        elif current_user_role == "Unit Personnel" and new_user_role in [
            "Super Admin",
            "Unit Admin",
        ]:
            return {
                "status": ddserr.AccessDeniedError.code.value,
                "message": ddserr.AccessDeniedError.description,
            }
        elif current_user_role == "Project Owner" and new_user_role in [
            "Super Admin",
            "Unit Admin",
            "Unit Personnel",
        ]:
            return {
                "status": ddserr.AccessDeniedError.code.value,
                "message": ddserr.AccessDeniedError.description,
            }
        elif current_user_role == "Researcher":
            return {
                "status": ddserr.AccessDeniedError.code.value,
                "message": ddserr.AccessDeniedError.description,
            }

        # Create invite row
        new_invite = models.Invite(
            email=email,
            role=("Researcher" if new_user_role == "Project Owner" else new_user_role),
        )

        # Create URL safe token for invitation link
        token = encrypted_jwt_token(
            username="",
            sensitive_content=generate_invite_key_pair(invite=new_invite).hex(),
            expires_in=datetime.timedelta(
                hours=flask.current_app.config["INVITATION_EXPIRES_IN_HOURS"]
            ),
            additional_claims={"inv": new_invite.email},
        )

        # Create link for invitation email
        link = flask.url_for("auth_blueprint.confirm_invite", token=token, _external=True)

        # Quick search gave this as the URL length limit.
        if len(link) >= 2048:
            flask.current_app.logger.error(
                "Invitation link was not possible to create due to length."
            )
            return {
                "message": "Invite failed due to server error",
                "status": http.HTTPStatus.INTERNAL_SERVER_ERROR,
            }

        projects_not_shared = {}
        goahead = False
        # Append invite to unit if applicable
        if new_invite.role in ["Unit Admin", "Unit Personnel"]:
            # TODO Change / move this later. This is just so that we can add an initial Unit Admin.
            if auth.current_user().role == "Super Admin":
                if unit:
                    unit_row = models.Unit.query.filter_by(public_id=unit).one_or_none()
                    if not unit_row:
                        raise ddserr.DDSArgumentError(message="Invalid unit publid id.")

                    unit_row.invites.append(new_invite)
                    goahead = True
                else:
                    raise ddserr.DDSArgumentError(
                        message="You need to specify a unit to invite a Unit Personnel or Unit Admin."
                    )

            if "Unit" in auth.current_user().role:
                # Give new unit user access to all projects of the unit
                auth.current_user().unit.invites.append(new_invite)
                for unit_project in auth.current_user().unit.projects:
                    if unit_project.is_active:
                        try:
                            share_project_private_key(
                                from_user=auth.current_user(),
                                to_another=new_invite,
                                from_user_token=dds_web.security.auth.obtain_current_encrypted_token(),
                                project=unit_project,
                            )
                        except ddserr.KeyNotFoundError as keyerr:
                            projects_not_shared[
                                unit_project.public_id
                            ] = "You do not have access to the project(s)"
                        else:
                            goahead = True

                if not project:  # specified project is disregarded for unituser invites
                    msg = f"{str(new_invite)} was successful."
                else:
                    msg = f"{str(new_invite)} was successful, but specification for {str(project)} dropped. Unit Users have automatic access to projects of their unit."

        else:
            db.session.add(new_invite)
            if project:
                try:
                    share_project_private_key(
                        from_user=auth.current_user(),
                        to_another=new_invite,
                        project=project,
                        from_user_token=dds_web.security.auth.obtain_current_encrypted_token(),
                        is_project_owner=new_user_role == "Project Owner",
                    )
                except ddserr.KeyNotFoundError as keyerr:
                    projects_not_shared[
                        project.public_id
                    ] = "You do not have access to the specified project."
                else:
                    goahead = True
            else:
                goahead = True

        # Compose and send email
        status_code = http.HTTPStatus.OK
        if goahead:
            try:
                db.session.commit()
            except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError) as sqlerr:
                db.session.rollback()
                raise ddserr.DatabaseError(
                    message=str(sqlerr),
                    alt_message=f"Invitation failed"
                    + (
                        ": Database malfunction."
                        if isinstance(sqlerr, sqlalchemy.exc.OperationalError)
                        else "."
                    ),
                ) from sqlerr

            AddUser.compose_and_send_email_to_user(
                userobj=new_invite, mail_type="invite", link=link
            )
            msg = f"{str(new_invite)} was successful."
        else:
            msg = (
                f"The user could not be added to the project(s)."
                if projects_not_shared
                else "Unknown error!"
            ) + " The invite did not succeed."
            status_code = ddserr.InviteError.code.value

        return {
            "email": new_invite.email,
            "message": msg,
            "status": status_code,
            "errors": projects_not_shared,
        }

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
    def add_to_project(whom, project, role, send_email=True):
        """Add existing user or invite to a project"""

        allowed_roles = ["Project Owner", "Researcher"]

        if role not in allowed_roles:
            return {
                "status": ddserr.AccessDeniedError.code.value,
                "message": (
                    "User Role should be either 'Project Owner' or "
                    "'Researcher' to be added to a project"
                ),
            }

        if whom.role not in allowed_roles:
            return {
                "status": ddserr.AccessDeniedError.code.value,
                "message": (
                    "Users affiliated with units can not be added to projects individually."
                ),
            }

        is_owner = role == "Project Owner"
        ownership_change = False

        if isinstance(whom, models.ResearchUser):
            project_user_row = models.ProjectUsers.query.filter_by(
                project_id=project.id, user_id=whom.username
            ).one_or_none()
        else:
            project_user_row = models.ProjectInviteKeys.query.filter_by(
                project_id=project.id, invite_id=whom.id
            ).one_or_none()

        if project_user_row:
            send_email = False
            if project_user_row.owner == is_owner:
                return {
                    "status": ddserr.RoleException.code.value,
                    "message": f"{str(whom)} is already associated with the {str(project)} in this capacity. ",
                }
            ownership_change = True
            project_user_row.owner = is_owner

        if not ownership_change:
            if isinstance(whom, models.ResearchUser):
                project.researchusers.append(
                    models.ProjectUsers(
                        project_id=project.id,
                        user_id=whom.username,
                        owner=is_owner,
                    )
                )

            try:
                share_project_private_key(
                    from_user=auth.current_user(),
                    to_another=whom,
                    from_user_token=dds_web.security.auth.obtain_current_encrypted_token(),
                    project=project,
                    is_project_owner=is_owner,
                )
            except ddserr.KeyNotFoundError as keyerr:
                return {
                    "message": (
                        "You do not have access to the current project. To get access, "
                        "ask the a user within the responsible unit to grant you access."
                    ),
                    "status": ddserr.AccessDeniedError.code.value,
                }

        try:
            db.session.commit()
        except (
            sqlalchemy.exc.SQLAlchemyError,
            sqlalchemy.exc.IntegrityError,
            sqlalchemy.exc.OperationalError,
        ) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise ddserr.DatabaseError(
                message=str(err),
                alt_message=f"Server Error: User was not associated with the project"
                + (
                    ": Database malfunction."
                    if isinstance(err, sqlalchemy.exc.OperationalError)
                    else "."
                ),
            ) from err

        # If project is already released and not expired, send mail to user
        send_email = send_email and project.current_status == "Available"
        if send_email:
            AddUser.compose_and_send_email_to_user(whom, "project_release", project=project)

        flask.current_app.logger.debug(
            f"{str(whom)} was given access to the {str(project)} as a {'Project Owner' if is_owner else 'Researcher'}."
        )

        return {
            "status": http.HTTPStatus.OK,
            "message": (
                f"{str(whom)} was given access to the "
                f"{str(project)} as a {'Project Owner' if is_owner else 'Researcher'}. An e-mail notification has{' not ' if not send_email else ' '}been sent."
            ),
        }

    @staticmethod
    @logging_bind_request
    def compose_and_send_email_to_user(userobj, mail_type, link=None, project=None):
        """Compose and send email"""
        if hasattr(userobj, "emails"):
            recipients = [x.email for x in userobj.emails]
        else:
            # userobj likely an invite
            recipients = [userobj.email]

        unit_name = None
        unit_email = None
        project_id = None
        deadline = None
        if auth.current_user().role in ["Unit Admin", "Unit Personnel"]:
            unit = auth.current_user().unit
            unit_name = unit.external_display_name
            unit_email = unit.contact_email
            sender_name = auth.current_user().name
            subject_subject = unit_name

        else:
            sender_name = auth.current_user().name
            subject_subject = sender_name

        # Fill in email subject with sentence subject
        if mail_type == "invite":
            subject = f"{subject_subject} invites you to the SciLifeLab Data Delivery System"
        elif mail_type == "project_release":
            subject = f"Project made available by {subject_subject} in the SciLifeLab Data Delivery System"
            project_id = project.public_id
            deadline = project.current_deadline.astimezone(datetime.timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S %Z"
            )
        else:
            raise ddserr.DDSArgumentError(message="Invalid mail type!")

        msg = flask_mail.Message(
            subject,
            recipients=recipients,
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
            f"mail/{mail_type}.txt",
            link=link,
            sender_name=sender_name,
            unit_name=unit_name,
            unit_email=unit_email,
            project_id=project_id,
            deadline=deadline,
        )
        msg.html = flask.render_template(
            f"mail/{mail_type}.html",
            link=link,
            sender_name=sender_name,
            unit_name=unit_name,
            unit_email=unit_email,
            project_id=project_id,
            deadline=deadline,
        )

        AddUser.send_email_with_retry(msg)


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

    @auth.login_required(role=["Unit Admin", "Unit Personnel", "Project Owner", "Researcher"])
    @logging_bind_request
    def delete(self):
        """Request deletion of own account."""
        current_user = auth.current_user()

        email_str = current_user.primary_email

        username = current_user.username

        proj_ids = None
        if current_user.role != "Super Admin":
            proj_ids = [proj.public_id for proj in current_user.projects]

        if current_user.role == "Unit Admin":
            num_admins = models.UnitUser.query.filter_by(
                unit_id=current_user.unit.id, is_admin=True
            ).count()
            if num_admins <= 3:
                raise ddserr.AccessDeniedError(
                    message=(
                        f"Your unit only has {num_admins} Unit Admins. "
                        "You cannot delete your account. "
                        "Invite a new Unit Admin first if you wish to proceed."
                    )
                )

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
                    "message": (
                        "The confirmation link has already "
                        f"been sent to your address {email_str}!"
                    ),
                    "status": http.HTTPStatus.OK,
                }

        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError) as sqlerr:
            db.session.rollback()
            raise ddserr.DatabaseError(
                message=str(sqlerr),
                alt_message=f"Creation of self-deletion request failed"
                + (
                    ": Database malfunction."
                    if isinstance(sqlerr, sqlalchemy.exc.OperationalError)
                    else "."
                ),
            ) from sqlerr

        # Create link for deletion request email
        link = flask.url_for("auth_blueprint.confirm_self_deletion", token=token, _external=True)
        subject = f"Confirm deletion of your user account {username} in the SciLifeLab Data Delivery System"

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
            projects=proj_ids,
        )
        msg.html = flask.render_template(
            "mail/deletion_request.html",
            link=link,
            sender_name=current_user.name,
            projects=proj_ids,
        )

        mail.send(msg)

        flask.current_app.logger.info(
            f"The user account {username} / {email_str} ({current_user.role}) "
            "has requested self-deletion."
        )

        return {
            "message": (
                "Requested account deletion initiated. An e-mail with a "
                f"confirmation link has been sent to your address {email_str}!"
            ),
        }


class UserActivation(flask_restful.Resource):
    """Endpoint to reactivate/deactivate users in the system

    Unit Admins can reactivate/deactivate unitusers. Super admins can reactivate/deactivate any user.
    """

    @auth.login_required(role=["Super Admin", "Unit Admin"])
    @logging_bind_request
    @json_required
    @handle_validation_errors
    def post(self):
        # Verify that user specified
        json_input = flask.request.json

        if "email" not in json_input:
            raise ddserr.DDSArgumentError(message="User email missing.")

        try:
            user = user_schemas.UserSchema().load({"email": json_input.pop("email")})
        except sqlalchemy.exc.OperationalError as err:
            raise ddserr.DatabaseError(message=str(err), alt_message="Unexpected database error.")

        if not user:
            raise ddserr.NoSuchUserError()

        # Verify that the action is specified -- reactivate or deactivate
        action = json_input.get("action")
        if not action:
            raise ddserr.DDSArgumentError(
                message="Please provide an action 'deactivate' or 'reactivate' for this request."
            )

        user_email_str = user.primary_email
        current_user = auth.current_user()

        if current_user.role == "Unit Admin":
            # Unit Admin can only activate/deactivate Unit Admins and personnel
            if user.role not in ["Unit Admin", "Unit Personnel"]:
                raise ddserr.AccessDeniedError(
                    message=(
                        "You can only activate/deactivate users with "
                        "the role Unit Admin or Unit Personnel."
                    )
                )

            if current_user.unit != user.unit:
                raise ddserr.AccessDeniedError(
                    message=(
                        "As a Unit Admin, you can only activate/deactivate other Unit Admins or "
                        "Unit Personnel within your specific unit."
                    )
                )

        if current_user == user:
            raise ddserr.AccessDeniedError(message=f"You cannot {action} your own account!")

        if (action == "reactivate" and user.is_active) or (
            action == "deactivate" and not user.is_active
        ):
            raise ddserr.DDSArgumentError(message=f"User is already {action}d!")

        # TODO: Check if user has lost access to any projects and if so, grant access again.
        if action == "reactivate":
            user.active = True

            # TODO: Super admins (current_user) don't have access to projects currently, how handle this?
            list_of_projects = None
            if user.role in ["Project Owner", "Researcher"]:
                list_of_projects = [x.project for x in user.project_associations]
            elif user.role in ["Unit Personnel", "Unit Admin"]:
                list_of_projects = user.unit.projects

            from dds_web.api.project import ProjectAccess  # Needs to be here because of circ.import

            ProjectAccess.give_project_access(
                project_list=list_of_projects, current_user=current_user, user=user
            )

        else:
            user.active = False

        try:
            db.session.commit()
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError) as err:
            db.session.rollback()
            raise ddserr.DatabaseError(
                message=str(err),
                alt_message=f"Unexpected database error"
                + (
                    ": Database malfunction."
                    if isinstance(err, sqlalchemy.exc.OperationalError)
                    else "."
                ),
            ) from err
        msg = (
            f"The user account {user.username} ({user_email_str}, {user.role}) "
            f" has been {action}d successfully been by {current_user.name} ({current_user.role})."
        )
        flask.current_app.logger.info(msg)

        with structlog.threadlocal.bound_threadlocal(
            who={"user": user.username, "role": user.role},
            by_whom={"user": current_user.username, "role": current_user.role},
        ):
            action_logger.info(self.__class__)

        return {
            "message": (
                f"You successfully {action}d the account {user.username} "
                f"({user_email_str}, {user.role})!"
            )
        }


class DeleteUser(flask_restful.Resource):
    """Endpoint to remove users from the system

    Unit Admins can delete Unit Admins and Unit Personnel. Super admins can delete any user."""

    @auth.login_required(role=["Super Admin", "Unit Admin"])
    @logging_bind_request
    @handle_validation_errors
    def delete(self):
        """Delete user or invite in the DDS."""
        current_user = auth.current_user()

        json_info = flask.request.json
        if json_info:
            is_invite = json_info.pop("is_invite", False)
            if is_invite:
                email = self.delete_invite(email=json_info.get("email"))
                return {
                    "message": ("The invite connected to email " f"'{email}' has been deleted.")
                }

        try:
            user = user_schemas.UserSchema().load(json_info)
        except sqlalchemy.exc.OperationalError as err:
            raise ddserr.DatabaseError(message=str(err), alt_message="Unexpected database error.")

        if not user:
            raise ddserr.UserDeletionError(
                message=(
                    "This e-mail address is not associated with a user in the DDS, "
                    "make sure it is not misspelled."
                )
            )

        user_email_str = user.primary_email
        current_user = auth.current_user()

        if current_user.role == "Unit Admin":
            if user.role not in ["Unit Admin", "Unit Personnel"]:
                raise ddserr.UserDeletionError(
                    message="You can only delete users with the role Unit Admin or Unit Personnel."
                )
            if current_user.unit != user.unit:
                raise ddserr.UserDeletionError(
                    message=(
                        "As a Unit Admin, you're can only delete Unit Admins "
                        "and Unit Personnel within your specific unit."
                    )
                )

        if current_user == user:
            raise ddserr.UserDeletionError(
                message="To delete your own account, use the '--self' flag instead!"
            )

        self.delete_user(user)

        msg = (
            f"The user account {user.username} ({user_email_str}, {user.role}) has been "
            f"terminated successfully been by {current_user.name} ({current_user.role})."
        )
        flask.current_app.logger.info(msg)

        with structlog.threadlocal.bound_threadlocal(
            who={"user": user.username, "role": user.role},
            by_whom={"user": current_user.username, "role": current_user.role},
        ):
            action_logger.info(self.__class__)

        return {
            "message": (
                f"You successfully deleted the account {user.username} "
                f"({user_email_str}, {user.role})!"
            )
        }

    @staticmethod
    def delete_user(user):
        try:
            parent_user = models.User.query.get(user.username)
            db.session.delete(parent_user)
            db.session.commit()
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError) as err:
            db.session.rollback()
            raise ddserr.DatabaseError(
                message=str(err),
                alt_message=f"Failed to delete user"
                + (
                    ": Database malfunction."
                    if isinstance(err, sqlalchemy.exc.OperationalError)
                    else "."
                ),
            ) from err

    @staticmethod
    def delete_invite(email):
        current_user_role = auth.current_user().role
        try:
            unanswered_invite = user_schemas.UnansweredInvite().load({"email": email})
            if unanswered_invite:
                if current_user_role == "Super Admin" or (
                    current_user_role == "Unit Admin"
                    and unanswered_invite.role in ["Unit Admin", "Unit Personnel", "Researcher"]
                ):
                    db.session.delete(unanswered_invite)
                    db.session.commit()
                else:
                    raise ddserr.AccessDeniedError(
                        message="You do not have the correct permissions to delete this invite."
                    )
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError) as err:
            db.session.rollback()
            flask.current_app.logger.error(
                "The invite connected to the email "
                f"{email or '[no email provided]'} was not deleted."
            )
            raise ddserr.DatabaseError(
                message=str(err),
                alt_message=f"Failed to delete invite"
                + (
                    ": Database malfunction."
                    if isinstance(err, sqlalchemy.exc.OperationalError)
                    else "."
                ),
            ) from err

        return email


class RemoveUserAssociation(flask_restful.Resource):
    @auth.login_required(role=["Unit Admin", "Unit Personnel", "Project Owner", "Researcher"])
    @logging_bind_request
    @json_required
    @handle_validation_errors
    def post(self):
        """Remove a user from a project"""
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)
        json_input = flask.request.json

        if not (user_email := json_input.get("email")):
            raise ddserr.DDSArgumentError(message="User email missing.")

        # Check if email is registered to a user
        try:
            existing_user = user_schemas.UserSchema().load({"email": user_email})
        except sqlalchemy.exc.OperationalError as err:
            raise ddserr.DatabaseError(message=str(err), alt_message="Unexpected database error.")

        if not existing_user:
            raise ddserr.NoSuchUserError(
                f"The user with email '{user_email}' does not have access to the specified project."
                " Cannot remove non-existent project access."
            )

        user_in_project = False
        for user_association in project.researchusers:
            if user_association.user_id == existing_user.username:
                user_in_project = True
                db.session.delete(user_association)
                project_user_key = models.ProjectUserKeys.query.filter_by(
                    project_id=project.id, user_id=existing_user.username
                ).first()
                if project_user_key:
                    db.session.delete(project_user_key)

        if not user_in_project:
            raise ddserr.NoSuchUserError(
                f"The user with email '{user_email}' does not have access to the specified project."
                " Cannot remove non-existent project access."
            )

        try:
            db.session.commit()
        except (
            sqlalchemy.exc.SQLAlchemyError,
            sqlalchemy.exc.IntegrityError,
            sqlalchemy.exc.OperationalError,
        ) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise ddserr.DatabaseError(
                message=str(err),
                alt_message=f"Server Error: Removing user association with the project has not succeeded"
                + (
                    ": Database malfunction."
                    if isinstance(err, sqlalchemy.exc.OperationalError)
                    else "."
                ),
            ) from err

        flask.current_app.logger.debug(
            f"User {existing_user.username} no longer associated with project {project.public_id}."
        )

        return {
            "message": f"User with email {user_email} no longer associated with {project.public_id}."
        }


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
        secondfactor_method = "TOTP" if auth.current_user().totp_enabled else "HOTP"
        return {
            "message": "Please take this token to /user/second_factor to authenticate with MFA!",
            "token": encrypted_jwt_token(
                username=auth.current_user().username,
                sensitive_content=flask.request.authorization.get("password"),
            ),
            "secondfactor_method": secondfactor_method,
        }


class SecondFactor(flask_restful.Resource):
    """Take in and verify an authentication one-time code entered by an authenticated user with basic credentials"""

    @auth.login_required
    @handle_validation_errors
    def get(self):

        try:
            token_schemas.TokenSchema().load(flask.request.json)
        except marshmallow.ValidationError as err:
            raise ddserr.AuthenticationError(message=err.messages)

        token_claims = dds_web.security.auth.obtain_current_encrypted_token_claims()

        return {"token": update_token_with_mfa(token_claims)}


class RequestTOTPActivation(flask_restful.Resource):
    """Request to switch from HOTP to TOTP for second factor authentication."""

    @auth.login_required
    def post(self):

        user = auth.current_user()
        if user.totp_enabled:
            return {"message": "Nothing to do, TOTP is already enabled for this user."}

        # Not really necessary to encrypt this
        token = encrypted_jwt_token(
            username=user.username,
            sensitive_content=None,
            expires_in=datetime.timedelta(
                seconds=3600,
            ),
            additional_claims={"act": "totp"},  # Open for suggestions
        )

        link = flask.url_for("auth_blueprint.activate_totp", token=token, _external=True)
        # Send activation token to email to work as a validation step
        # TODO: refactor this since the email sending code is replicated in many places
        recipients = [user.primary_email]

        # Fill in email subject with sentence subject
        subject = f"Request to activate TOTP for SciLifeLab Data Delivery System"

        msg = flask_mail.Message(
            subject,
            recipients=recipients,
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
            f"mail/request_activate_totp.txt",
            link=link,
        )
        msg.html = flask.render_template(
            f"mail/request_activate_totp.html",
            link=link,
        )

        AddUser.send_email_with_retry(msg)
        return {"message": "Please check your email and follow the attached link to activate TOTP."}


class ShowUsage(flask_restful.Resource):
    """Calculate and display the amount of GB hours and the total cost."""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    def get(self):
        current_user = auth.current_user()

        # Check that user is unit account
        if current_user.role not in ["Unit Admin", "Unit Personnel"]:
            raise ddserr.AccessDeniedError(
                "Access denied - only unit accounts can get invoicing information."
            )

        # Get unit info from table (incl safespring proj name)
        try:
            unit_info = models.Unit.query.filter(
                models.Unit.id == sqlalchemy.func.binary(current_user.unit_id)
            ).first()
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError) as err:
            flask.current_app.logger.exception(err)
            raise ddserr.DatabaseError(
                message=str(err),
                alt_message=f"Failed to get unit information."
                + (
                    ": Database malfunction."
                    if isinstance(err, sqlalchemy.exc.OperationalError)
                    else "."
                ),
            ) from err

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

        return {
            "total_usage": {
                "gbhours": round(total_gbhours_db, 2),
                "cost": round(total_cost_db, 2),
            },
            "project_usage": usage,
        }


class UnitUsers(flask_restful.Resource):
    """List unit users."""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    @handle_db_error
    def get(self):
        """List unit users within the unit the current user is connected to, or the one defined by a superadmin."""
        unit_users = {}

        if auth.current_user().role == "Super Admin":
            json_input = flask.request.json
            if not json_input:
                raise ddserr.DDSArgumentError(message="Unit public id missing.")

            unit = json_input.get("unit")
            if not unit:
                raise ddserr.DDSArgumentError(message="Unit public id missing.")

            unit_row = models.Unit.query.filter_by(public_id=unit).one_or_none()
            if not unit_row:
                raise ddserr.DDSArgumentError(
                    message=f"There is no unit with the public id '{unit}'."
                )
        else:
            unit_row = auth.current_user().unit

        keys = ["Name", "Username", "Email", "Role", "Active"]

        unit_users = [
            {
                "Name": user.name,
                "Username": user.username,
                "Email": user.primary_email,
                "Role": user.role,
                "Active": user.is_active,
            }
            for user in unit_row.users
        ]

        return {"users": unit_users, "keys": keys, "unit": unit_row.name}
