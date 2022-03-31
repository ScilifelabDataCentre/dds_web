####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import base64
import datetime
import io
import re

# Installed
import flask
import werkzeug
import flask_login
import itsdangerous
import qrcode
import qrcode.image.svg
import sqlalchemy

# Own Modules
import dds_web.utils
import dds_web.errors as ddserr
import dds_web.security
from dds_web import forms, db, limiter
from dds_web.api import db_tools
from dds_web.api.dds_decorators import logging_bind_request
from dds_web.api.schemas import user_schemas
from dds_web.api.project import UserProjects
from dds_web.api.user import DeleteUser
from dds_web.database import models
from dds_web.security.project_user_keys import update_user_keys_for_password_change

auth_blueprint = flask.Blueprint("auth_blueprint", __name__)

####################################################################################################
# ERROR HANDLING ################################################################## ERROR HANDLING #
####################################################################################################


@auth_blueprint.errorhandler(werkzeug.exceptions.HTTPException)
def bad_request(error):
    """Handle user deletion errors."""
    try:
        message = error.message
    except AttributeError:
        message = ""
    flask.current_app.logger.error(f"{error.code}: {message}")
    return flask.make_response(
        flask.render_template("error.html", message=message, error_code=error.code), error.code
    )


####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


@auth_blueprint.route("/confirm_invite/<token>", methods=["GET"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    error_message=ddserr.TooManyRequestsError.description,
)
@logging_bind_request
def confirm_invite(token):
    """Confirm invitation."""
    # Verify token and, on success, get row from invite table
    try:
        email, invite_row = dds_web.security.auth.verify_invite_token(token)
    except ddserr.AuthenticationError as err:
        flask.flash("This invitation link has expired or is invalid.", "warning")
        return flask.redirect(flask.url_for("pages.home"))

    # Check the invite exists
    if not invite_row:
        if email and dds_web.utils.email_in_db(email=email):
            flask.flash("Registration has already been completed.", "warning")
            return flask.make_response(flask.render_template("user/userexists.html"))
        else:
            # Perhaps the invite has been cancelled by an admin
            flask.flash("This invitation link is invalid.", "warning")
            return flask.redirect(flask.url_for("pages.home"))

    # Save encrypted token to be reused at registration
    # token is in the session already if the user refreshes the page
    if "invite_token" not in flask.session:
        # New visit or session has expired
        flask.session["invite_token"] = token

    form = forms.RegistrationForm()

    # Prefill fields - unit readonly if filled, otherwise disabled
    # These should only be used for display to user and not when actually registering
    # the user, then the values should be fetched from the database again.
    # form.unit_name.render_kw = {"disabled": True}
    # if invite_row.unit:  # backref to unit
    #     form.unit_name.data = invite_row.unit.name
    #     form.unit_name.render_kw = {"readonly": True}

    form.email.data = email
    suggested_username = email.split("@")[0]

    if dds_web.utils.valid_chars_in_username(
        suggested_username
    ) and not dds_web.utils.username_in_db(suggested_username):
        form.username.data = suggested_username

    return flask.render_template(
        "user/register.html",
        form=form,
        unit=invite_row.unit.name if invite_row.unit else None,
    )


@auth_blueprint.route("/register", methods=["POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    error_message=ddserr.TooManyRequestsError.description,
)
def register():
    """Handles the creation of a new user"""
    form = dds_web.forms.RegistrationForm()

    # Two reasons are possible for the token to be None.
    # The most likely reason is that the session has expired (given by PERMANENT_SESSION_LIFETIME config variable)
    # Less likely is that the confirm_invite was not called before posting the registration form.
    if flask.session.get("invite_token") is None:
        flask.current_app.logger.info(
            "No token has been found in session when posting to register."
        )
        flask.flash(
            "Error in registration process, please go back and use the link in the invitation email again.",
            "danger",
        )
        return flask.redirect(flask.url_for("pages.home"))

    # Validate form - validators defined in form class
    if form.validate_on_submit():
        # Create new user row by loading form data into schema
        try:
            new_user = user_schemas.NewUserSchema().load(form.data)
        except Exception as err:
            # This should never happen since the form is validated
            # Any error catched here is likely a bug/issue
            flask.current_app.logger.warning(err)
            flask.flash("Error in registration process, please try again.", "danger")
            return flask.redirect(flask.url_for("pages.home"))

        flask.flash("Registration successful!", "success")
        return flask.make_response(flask.render_template("user/userexists.html"))

    # Go to registration form
    return flask.render_template("user/register.html", form=form)


@auth_blueprint.route("/activate_totp/<token>", methods=["GET", "POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    methods=["GET", "POST"],
    error_message=ddserr.TooManyRequestsError.description,
)
@flask_login.login_required
def activate_totp(token):
    user = flask_login.current_user

    form = forms.ActivateTOTPForm()

    dds_web.security.auth.verify_activate_totp_token(token, current_user=user)

    if user.totp_enabled:
        flask.flash("Two-factor authentication via TOTP is already enabled.")
        return flask.redirect(flask.url_for("pages.home"))

    # Don't change secret on page reload
    if not user.totp_initiated:
        user.setup_totp_secret()

    totp_secret, totp_uri = user.get_totp_secret()

    # QR code generation
    image = qrcode.make(totp_uri, image_factory=qrcode.image.svg.SvgImage)
    stream = io.BytesIO()
    image.save(stream)

    # POST request
    if form.validate_on_submit():
        try:
            user.verify_TOTP(form.totp.data.encode())
        except ddserr.AuthenticationError:
            flask.flash("Invalid two-factor authentication code.")
            return (
                flask.render_template(
                    "user/activate_totp.html",
                    totp_secret=base64.b32encode(totp_secret).decode("utf-8"),
                    totp_uri=totp_uri,
                    qr_code=stream.getvalue().decode("utf-8"),
                    token=token,
                    form=form,
                ),
                200,
                {
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )

        user.activate_totp()

        flask.flash("Two-factor authentication via TOTP has been enabled.")
        return flask.redirect(flask.url_for("pages.home"))

    return (
        flask.render_template(
            "user/activate_totp.html",
            totp_secret=base64.b32encode(totp_secret).decode("utf-8"),
            totp_uri=totp_uri,
            qr_code=stream.getvalue().decode("utf-8"),
            token=token,
            form=form,
        ),
        200,
        {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@auth_blueprint.route("/cancel_2fa", methods=["POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    methods=["POST"],
    error_message=ddserr.TooManyRequestsError.description,
)
def cancel_2fa():
    flask.session.pop("2fa_initiated_token", None)
    return flask.redirect(flask.url_for("auth_blueprint.login"))


@auth_blueprint.route("/confirm_2fa", methods=["GET", "POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    methods=["GET", "POST"],
    error_message=ddserr.TooManyRequestsError.description,
)
def confirm_2fa():
    """Finalize login by validating the authentication one-time token."""
    # Redirect to index if user is already authenticated
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for("pages.home"))

    next_target = flask.request.args.get("next")
    # is_safe_url should check if the url is safe for redirects.
    if next_target and not dds_web.utils.is_safe_url(next_target):
        return flask.abort(400)

    # Check user has initiated 2FA
    token = flask.session.get("2fa_initiated_token")
    try:
        user = dds_web.security.auth.verify_token_no_data(token)
    except ddserr.AuthenticationError:
        flask.flash(
            "Error: Please initiate a log in before entering the one-time authentication code.",
            "warning",
        )
        return flask.redirect(flask.url_for("auth_blueprint.login", next=next_target))
    except Exception as e:
        flask.current_app.logger.exception(e)
        flask.flash(
            "Error: Second factor could not be validated due to an internal server error.",
            "danger",
        )
        return flask.redirect(flask.url_for("auth_blueprint.login", next=next_target))

    if user.totp_enabled:
        form = forms.Confirm2FACodeTOTPForm()
    else:
        form = forms.Confirm2FACodeHOTPForm()

    cancel_form = forms.Cancel2FAForm()

    # Valid 2fa initiated token, but user does not exist (should never happen) or is inactive (could happen)
    # Currently same error for both, not vital, they get message to contact us
    if not user:
        flask.session.pop("2fa_initiated_token", None)
        flask.flash("Your account is not active. Contact Data Centre.", "warning")
        return flask.redirect(flask.url_for("auth_blueprint.login", next=next_target))

    if form.validate_on_submit():

        if user.totp_enabled:
            twofactor_value = form.totp.data
            twofactor_verify = user.verify_TOTP
        else:
            twofactor_value = form.hotp.data
            twofactor_verify = user.verify_HOTP

        # Raises authenticationerror if invalid
        try:
            twofactor_verify(twofactor_value.encode())
        except ddserr.AuthenticationError:
            flask.flash("Invalid one-time code.", "warning")
            return flask.redirect(
                flask.url_for(
                    "auth_blueprint.confirm_2fa",
                    form=form,
                    cancel_form=cancel_form,
                    next=next_target,
                    using_totp=user.totp_enabled,
                )
            )

        # Correct username, password and twofactor code --> log user in
        flask_login.login_user(user)
        flask.flash("Logged in successfully.", "success")
        # Remove token from session
        flask.session.pop("2fa_initiated_token", None)
        # Next is assured to be url_safe above
        return flask.redirect(next_target or flask.url_for("pages.home"))

    else:
        return flask.render_template(
            "user/confirm2fa.html", form=form, cancel_form=cancel_form, next=next_target, using_totp=user.totp_enabled
        )


@auth_blueprint.route("/login", methods=["GET", "POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    methods=["POST"],
    error_message=ddserr.TooManyRequestsError.description,
)
def login():
    """Initiate a login by validating username password and sending a authentication one-time code"""

    next_target = flask.request.args.get("next")
    # is_safe_url should check if the url is safe for redirects.
    if next_target and not dds_web.utils.is_safe_url(next_target):
        return flask.abort(400)

    # Redirect to next or index if user is already authenticated
    if flask_login.current_user.is_authenticated:
        return flask.redirect(next_target or flask.url_for("pages.home"))

    # Display greeting message, if applicable
    if next_target and re.search("confirm_deletion", next_target):
        flask.flash("Please log in to confirm your account deletion.", "warning")

    # Check if for is filled in and correctly (post)
    form = forms.LoginForm()
    if form.validate_on_submit():
        # Get user from database
        user = models.User.query.get(form.username.data)

        # Unsuccessful login
        if not user or not user.verify_password(input_password=form.password.data):
            flask.flash("Invalid username or password.", "warning")
            return flask.redirect(
                flask.url_for("auth_blueprint.login", next=next_target)
            )  # Try login again

        # Correct credentials still needs 2fa
        if not user.totp_enabled:
            # Send 2fa token to user's email
            if dds_web.security.auth.send_hotp_email(user):
                flask.flash("One-Time Code has been sent to your primary email.")

        # Generate signed token that indicates that the user has authenticated
        token_2fa_initiated = dds_web.security.tokens.jwt_token(
            user.username, expires_in=datetime.timedelta(minutes=15)
        )

        flask.session["2fa_initiated_token"] = token_2fa_initiated
        return flask.redirect(flask.url_for("auth_blueprint.confirm_2fa", next=next_target))

    # Go to login form (get)
    return flask.render_template("user/login.html", form=form, next=next_target)


@auth_blueprint.route("/logout", methods=["GET"])
@flask_login.login_required
def logout_get():
    """DDS log out page."""
    form = forms.LogoutForm()
    return flask.render_template("user/logout.html", form=form)


@auth_blueprint.route("/logout", methods=["POST"])
@flask_login.login_required
@logging_bind_request
def logout_post():
    """Logout user."""

    if flask_login.current_user.is_authenticated:
        flask_login.logout_user()

    return flask.redirect(flask.url_for("pages.home"))


@auth_blueprint.route("/reset_password", methods=["GET", "POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    methods=["POST"],
    error_message=ddserr.TooManyRequestsError.description,
)
@logging_bind_request
def request_reset_password():
    """Request to reset password when password is lost."""
    # Reset forgotten password only allowed if logged out
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for("pages.home"))

    # Validate form
    form = forms.RequestResetForm()
    if form.validate_on_submit():
        email = models.Email.query.filter_by(email=form.email.data).first()
        if email.user.is_active:
            token = dds_web.security.tokens.encrypted_jwt_token(
                username=email.user.username,
                sensitive_content=None,
                expires_in=datetime.timedelta(
                    seconds=3600,
                ),
                additional_claims={"rst": "pwd"},
            )

            # Create row in password reset table
            ongoing_password_reset = models.PasswordReset.query.filter_by(
                email=email.email
            ).one_or_none()
            if ongoing_password_reset:
                ongoing_password_reset.issued = dds_web.utils.current_time()
                ongoing_password_reset.valid = True
            else:
                new_password_reset = models.PasswordReset(
                    user=email.user, email=email.email, issued=dds_web.utils.current_time()
                )
                db.session.add(new_password_reset)
            db.session.commit()

            dds_web.utils.send_reset_email(email_row=email, token=token)
            flask.flash("An email has been sent with instructions to reset your password.")
            return flask.redirect(flask.url_for("auth_blueprint.login"))

        flask.flash("Your account is deactivated. You cannot reset your password.", "warning")

    # Show form
    return flask.render_template("user/request_reset_password.html", form=form)


@auth_blueprint.route("/reset_password/<token>", methods=["GET", "POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    error_message=ddserr.TooManyRequestsError.description,
)
def reset_password(token):
    """Perform the password reset when password is lost."""
    # Go to index page if already logged in
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for("pages.home"))

    # Verify that the token is valid and contains enough info
    try:
        user = dds_web.security.auth.verify_password_reset_token(token=token)
        if not user.is_active:
            flask.flash("Your account is not active. You cannot reset your password.", "warning")
            return flask.redirect(flask.url_for("pages.home"))

        password_reset_row = models.PasswordReset.query.filter_by(
            user_id=user.username
        ).one_or_none()
        if not password_reset_row:
            flask.flash("No information on requested password reset.")
            return flask.redirect(flask.url_for("pages.home"))
        if not password_reset_row.valid:
            flask.flash(
                "You have already used this link to change your password. "
                "Please request a new password reset if you wish to continue."
            )
            return flask.redirect(flask.url_for("pages.home"))

    except ddserr.AuthenticationError:
        flask.flash("That is an invalid or expired token", "warning")
        return flask.redirect(flask.url_for("pages.home"))

    # Get form for reseting password
    form = forms.ResetPasswordForm()

    # Validate form
    if form.validate_on_submit():
        # Clear out hotp
        user.reset_current_HOTP()

        # Delete project user keys for user
        for project_user_key in user.project_user_keys:
            db.session.delete(project_user_key)
        db.session.commit()

        # Reset user keys, will be regenerated on setting new password
        user.kd_salt = None
        user.nonce = None
        user.public_key = None
        user.private_key = None

        # Update user password
        user.password = form.password.data

        # Set password reset row as invalid
        password_reset_row.valid = False
        password_reset_row.changed = dds_web.utils.current_time()
        db.session.commit()

        flask.flash("Your password has been updated! You are now able to log in.", "success")
        flask.session["reset_token"] = token
        return flask.redirect(flask.url_for("auth_blueprint.password_reset_completed"))

    # Go to form
    return flask.render_template("user/reset_password.html", form=form)


@auth_blueprint.route("/password_reset_completed", methods=["GET"])
@logging_bind_request
def password_reset_completed():
    """Landing page after password reset"""

    token = flask.session["reset_token"]
    flask.session.pop("reset_token", None)
    try:
        user = dds_web.security.auth.verify_password_reset_token(token=token)
        if not user.is_active:
            flask.flash("Your account is not active.", "warning")
            return flask.redirect(flask.url_for("pages.home"))
    except ddserr.AuthenticationError:
        flask.flash("That is an invalid or expired token", "warning")
        return flask.redirect(flask.url_for("pages.home"))

    units_to_contact = {}
    unit_admins_to_contact = {}

    if user.role != "Super Admin":
        for project in user.projects:
            if user.role == "Unit Admin":
                users = (
                    db.session.query(models.User)
                    .join(models.UnitUser)
                    .join(models.Email)
                    .with_entities(
                        models.User.username,
                        models.User.name,
                        models.UnitUser.unit_id,
                        models.UnitUser.is_admin,
                        models.Email.email,
                    )
                    .filter(models.UnitUser.unit_id == user.unit_id)
                    .filter(models.UnitUser.is_admin == True)
                    .filter(models.User.username != user.username)
                    .all()
                )
                email = (
                    db.session.query(models.Email)
                    .with_entities(models.Email.email)
                    .filter(models.Email.user_id == user.username)
                    .first()
                )

                unit_admins_to_contact = users
            else:
                if project.responsible_unit.external_display_name not in units_to_contact:
                    units_to_contact[
                        project.responsible_unit.external_display_name
                    ] = project.responsible_unit.contact_email

        if len(unit_admins_to_contact) > 0:
            for unit_admin in unit_admins_to_contact:
                dds_web.utils.send_project_access_reset_email(unit_admin, email[0], token)

    return flask.render_template(
        "user/password_reset_completed.html", units_to_contact=units_to_contact
    )


@auth_blueprint.route("/change_password", methods=["GET", "POST"])
@flask_login.login_required
def change_password():
    """Change password by entering the old password."""

    # Validate form
    form = forms.ChangePasswordForm()
    if form.validate_on_submit():
        # Change password
        flask_login.current_user.password = form.new_password.data
        update_user_keys_for_password_change(
            user=flask_login.current_user,
            current_password=form.current_password.data,
            new_password=form.new_password.data,
        )
        db.session.commit()

        flask_login.logout_user()
        flask.flash(
            "You have successfully changed your password. Please log in again with your new password.",
            "success",
        )
        return flask.redirect(flask.url_for("auth_blueprint.login"))

    # Show form
    return flask.render_template("user/change_password.html", form=form)


@auth_blueprint.route("/confirm_deletion/<token>", methods=["GET"])
@flask_login.login_required
@logging_bind_request
def confirm_self_deletion(token):
    """Confirm user deletion."""
    s = itsdangerous.URLSafeTimedSerializer(flask.current_app.config.get("SECRET_KEY"))

    try:

        # Get email from token, overwrite the one from login if applicable
        email = s.loads(token, salt="email-delete", max_age=604800)

        # Check that the email is registered on the current user:
        if email not in [email.email for email in flask_login.current_user.emails]:
            msg = "The email for user to be deleted is not registered on your account."
            flask.current_app.logger.warning(
                f"{msg} email: {email}: user: {flask_login.current_user}"
            )
            raise ddserr.UserDeletionError(message=msg)

        # Get row from deletion requests table
        deletion_request_row = models.DeletionRequest.query.filter(
            models.DeletionRequest.email == email
        ).first()

    except itsdangerous.exc.SignatureExpired as exc:

        email = db_tools.remove_user_self_deletion_request(flask_login.current_user)
        raise ddserr.UserDeletionError(
            message=f"Deletion request for {email} has expired. Please login to the DDS and request deletion anew."
        ) from exc
    except (itsdangerous.exc.BadSignature, itsdangerous.exc.BadTimeSignature) as exc:
        raise ddserr.UserDeletionError(
            message="Confirmation link is invalid. No action has been performed."
        ) from exc
    except sqlalchemy.exc.SQLAlchemyError as sqlerr:
        raise ddserr.DatabaseError(message=sqlerr) from sqlerr

    # Check if the user and the deletion request exists
    if deletion_request_row:
        try:
            user = user_schemas.UserSchema().load({"email": email})
            _ = db_tools.remove_user_self_deletion_request(user)
            DeleteUser.delete_user(user=user)

        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise ddserr.UserDeletionError(
                message=f"User deletion request for {user.username} / {user.primary_email.email} failed due to database error: {sqlerr}",
                alt_message=f"Deletion request for user {user.username} registered with {user.primary_email.email} failed for technical reasons. Please contact the unit for technical support!",
            )
        except sqlalchemy.exc.OperationalError as err:
            raise ddserr.DatabaseError(message=str(err), alt_message="Unexpected database error.")

        flask.session.clear()

        return flask.make_response(
            flask.render_template("user/userdeleted.html", username=user.username, initial=True)
        )
    else:
        return flask.make_response(
            flask.render_template("user/userdeleted.html", username=email, initial=False)
        )


@auth_blueprint.route("/account", methods=["GET"])
@flask_login.login_required
@logging_bind_request
def account_info():
    """User account page"""

    return flask.render_template("user/account.html", enumerate=enumerate)


@auth_blueprint.route("/projects", methods=["GET"])
@flask_login.login_required
@logging_bind_request
def projects_info():
    """User projects page"""
    projects_obj = UserProjects()
    projects = projects_obj.format_project_dict(flask_login.current_user)

    return flask.render_template("user/projects.html", projects=projects, enumerate=enumerate)
