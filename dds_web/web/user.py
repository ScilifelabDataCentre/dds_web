""""""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import datetime
import re

# Installed
import flask
import werkzeug
from dds_web.api.db_connector import DBConnector
import flask_login
import itsdangerous
import sqlalchemy
import marshmallow

# Own Modules
from dds_web import forms
from dds_web.database import models
import dds_web.utils
from dds_web import db, limiter
import dds_web.errors as ddserr
from dds_web.api.dds_decorators import logging_bind_request
from dds_web.api.schemas import user_schemas
import dds_web.security


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
    return flask.make_response(flask.render_template("error.html", message=message), error.code)


####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


@auth_blueprint.route("/", methods=["GET"])
@flask_login.login_required
def index():
    """DDS start page."""
    form = forms.LogoutForm()
    return flask.render_template("index.html", form=form)


@auth_blueprint.route("/confirm_invite/<token>", methods=["GET"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    error_message=ddserr.TooManyRequestsError.description,
)
@logging_bind_request
def confirm_invite(token):
    """Confirm invitation."""
    try:
        email = dds_web.security.auth.verify_invite_token_no_data(token)
    except Exception as err:
        flask.flash("This invitation link has expired or is invalid.", "danger")
        return flask.redirect(flask.url_for("auth_blueprint.index"))

    # Get row from invite table
    invite_row = models.Invite.query.filter(models.Invite.email == email).first()

    # Check the invite exists
    if not invite_row:
        if dds_web.utils.email_in_db(email=email):
            flask.flash("Registration already completed.")
            return flask.make_response(flask.render_template("user/userexists.html"))
        else:
            flask.flash("This invitation link has expired or is invalid.", "danger")
            return flask.redirect(flask.url_for("auth_blueprint.index"))

    # Save encrypted token to be reused at registration
    # token is in the session already if the user refreshes the page
    if not "invite_token" in flask.session:
        # New visit or session has expired
        flask.session["invite_token"] = token

    form = forms.RegistrationForm()

    # Prefill fields - unit readonly if filled, otherwise disabled
    # These should only be used for display to user and not when actually registering
    # the user, then the values should be fetched from the database again.
    form.unit_name.render_kw = {"disabled": True}
    if invite_row.unit:  # backref to unit
        form.unit_name.data = invite_row.unit.name
        form.unit_name.render_kw = {"readonly": True}

    form.email.data = email
    suggested_username = email.split("@")[0]

    if dds_web.utils.valid_chars_in_username(
        suggested_username
    ) and not dds_web.utils.username_in_db(suggested_username):
        form.username.data = suggested_username

    return flask.render_template("user/register.html", form=form)


@auth_blueprint.route("/register", methods=["POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    error_message=ddserr.TooManyRequestsError.description,
)
def register():
    """Handles the creation of a new user"""
    token = flask.session.get("invite_token")

    form = dds_web.forms.RegistrationForm()

    # Two reasons are possible for the token to be None.
    # The most likely reason is that the session has expired (given by PERMANENT_SESSION_LIFETIME config variable)
    # Less likely is that the confirm_invite was not called before posting the registration form.
    if token is None:
        flask.current_app.logger.info("No token found in session when posting to register.")
        flask.flash(
            "Error in registration process, please go back and use the link in the invitation email again."
        )
        return flask.redirect(flask.url_for("auth_blueprint.index"))

    # This method can raise exceptions, but they should occur very rarely since token should be verified
    # and therefore we don't need any special message to user.
    token_email, TKEK = dds_web.security.auth.verify_invite_token(token)

    # Validate form - validators defined in form class
    if form.validate_on_submit():
        # Create new user row by loading form data into schema
        try:
            new_user = user_schemas.NewUserSchema().load(
                {**form.data, "token_email": token_email, "TKEK": TKEK}
            )
        except Exception as err:
            # This should never happen since the form is validated
            # Any error catched here is likely a bug/issue
            flask.current_app.logger.warning(err)
            flask.flash("Error in registration process, please try again.")
            return flask.redirect(flask.url_for("auth_blueprint.index"))

        flask.session.pop("invite_token", None)
        flask.flash("Registration successful!")
        return flask.make_response(flask.render_template("user/userexists.html"))

    # Go to registration form
    return flask.render_template("user/register.html", form=form)


@auth_blueprint.route("/cancel_2fa", methods=["POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    methods=["POST"],
    error_message=ddserr.TooManyRequestsError.description,
)
def cancel_2fa():
    # Reset 2fa cookie
    redirect_to_login = flask.redirect(flask.url_for("auth_blueprint.login"))
    redirect_to_login.set_cookie("2fa_initiated_token", "", expires=0)
    return redirect_to_login


@auth_blueprint.route("/confirm_2fa", methods=["GET", "POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    methods=["GET", "POST"],
    error_message=ddserr.TooManyRequestsError.description,
)
def confirm_2fa():
    """Finalize login by validating the authentication one-time token"""

    # Redirect to index if user is already authenticated
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for("auth_blueprint.index"))

    form = forms.Confirm2FACodeForm()

    cancel_form = forms.Cancel2FAForm()

    next = flask.request.args.get("next")
    # is_safe_url should check if the url is safe for redirects.
    if next and not dds_web.utils.is_safe_url(next):
        return flask.abort(400)

    if form.validate_on_submit():
        try:
            token = flask.request.cookies["2fa_initiated_token"]
            user = dds_web.security.auth.verify_token_no_data(token)
        except ddserr.AuthenticationError as e:
            flask.flash(f"Error: Second factor could not be validated due to: {e}", "danger")
            return flask.redirect(flask.url_for("auth_blueprint.login", next=next))
        except Exception as e:
            flask.current_app.logger.exception(e)
            flask.flash(
                "Error: Second factor could not be validated due to an unknown error", "danger"
            )
            return flask.redirect(flask.url_for("auth_blueprint.login", next=next))

        hotp_value = form.hotp.data

        # Raises authenticationerror if invalid
        try:
            user.verify_HOTP(hotp_value.encode())
        except ddserr.AuthenticationError:
            flask.flash("Invalid one-time code.")
            return flask.redirect(
                flask.url_for(
                    "auth_blueprint.confirm_2fa", form=form, cancel_form=cancel_form, next=next
                )
            )

        # Correct username, password and hotp code --> log user in
        flask_login.login_user(user)
        # Remove token from cookies and make it expired
        flask.flash("Logged in successfully.")
        redirect_to_index = flask.redirect(next or flask.url_for("auth_blueprint.index"))
        redirect_to_index.set_cookie("2fa_initiated_token", "", expires=0)
        return redirect_to_index

    else:
        return flask.render_template(
            "user/confirm2fa.html", form=form, cancel_form=cancel_form, next=next
        )


@auth_blueprint.route("/login", methods=["GET", "POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    methods=["POST"],
    error_message=ddserr.TooManyRequestsError.description,
)
def login():
    """Initiate a login by validating username password and sending a authentication one-time code"""

    next = flask.request.args.get("next")
    # is_safe_url should check if the url is safe for redirects.
    if next and not dds_web.utils.is_safe_url(next):
        return flask.abort(400)

    # Redirect to next or index if user is already authenticated
    if flask_login.current_user.is_authenticated:
        return flask.redirect(next or flask.url_for("auth_blueprint.index"))

    # Display greeting message, if applicable
    if next and re.search("confirm_deletion", next):
        flask.flash("Please log in to confirm your account deletion.", "warning")

    # Check if for is filled in and correctly (post)
    form = forms.LoginForm()
    if form.validate_on_submit():
        # Get user from database
        user = models.User.query.get(form.username.data)

        # Unsuccessful login
        if not user or not user.verify_password(input_password=form.password.data):
            flask.flash("Invalid username or password.")
            return flask.redirect(
                flask.url_for("auth_blueprint.login", next=next)
            )  # Try login again

        # Correct credentials still needs 2fa

        # Send 2fa token to user's email
        if dds_web.security.auth.send_hotp_email(user):
            flask.flash("One-Time Code has been sent to your primary email.")

        # Generate signed token that indicates that the user has authenticated
        token_2fa_initiated = dds_web.security.tokens.jwt_token(
            user.username, expires_in=datetime.timedelta(minutes=15)
        )

        redirect_to_confirm = flask.redirect(flask.url_for("auth_blueprint.confirm_2fa", next=next))
        redirect_to_confirm.set_cookie("2fa_initiated_token", token_2fa_initiated)
        return redirect_to_confirm

    # Go to login form (get)
    return flask.render_template("user/login.html", form=form, next=next)


@auth_blueprint.route("/logout", methods=["POST"])
@flask_login.login_required
@logging_bind_request
def logout():
    """Logout user."""

    if flask_login.current_user.is_authenticated:
        flask_login.logout_user()

    return flask.redirect(flask.url_for("auth_blueprint.index"))


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
        return flask.redirect(flask.url_for("auth_blueprint.index"))

    # Validate form
    form = forms.RequestResetForm()
    if form.validate_on_submit():
        email = models.Email.query.filter_by(email=form.email.data).first()
        dds_web.utils.send_reset_email(email_row=email)
        flask.flash("An email has been sent with instructions to reset your password.", "info")
        return flask.redirect(flask.url_for("auth_blueprint.login"))

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
        return flask.redirect(flask.url_for("auth_blueprint.index"))

    # Verify that the token is valid and contains enough info
    user = models.User.verify_reset_token(token=token)
    if not user:
        flask.flash("That is an invalid or expired token", "warning")
        return flask.redirect(flask.url_for("auth_blueprint.request_reset_password"))

    # Get form for reseting password
    form = forms.ResetPasswordForm()

    # Validate form
    if form.validate_on_submit():
        user.password = form.password.data
        db.session.commit()
        flask.flash("Your password has been updated! You are now able to log in.", "success")
        return flask.redirect(flask.url_for("auth_blueprint.login"))

    # Go to form
    return flask.render_template("user/reset_password.html", form=form)


@auth_blueprint.route("/change_password", methods=["GET", "POST"])
@flask_login.login_required
def change_password():
    """Change password by entering the old password."""

    # Validate form
    form = forms.ChangePasswordForm()
    if form.validate_on_submit():
        # Change password
        flask_login.current_user.password = form.new_password.data
        db.session.commit()

        flask_login.logout_user()
        flask.flash("You have successfully changed your password.", "success")
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
            msg = f"The email for user to be deleted is not registered on your account."
            flask.current_app.logger.warning(
                f"{msg} email: {email}: user: {flask_login.current_user}"
            )
            raise ddserr.UserDeletionError(message=msg)

        # Get row from deletion requests table
        deletion_request_row = models.DeletionRequest.query.filter(
            models.DeletionRequest.email == email
        ).first()

    except itsdangerous.exc.SignatureExpired:

        email = DBConnector.remove_user_self_deletion_request(flask_login.current_user)
        raise ddserr.UserDeletionError(
            message=f"Deletion request for {email} has expired. Please login to the DDS and request deletion anew."
        )
    except (itsdangerous.exc.BadSignature, itsdangerous.exc.BadTimeSignature):
        raise ddserr.UserDeletionError(
            message=f"Confirmation link is invalid. No action has been performed."
        )
    except sqlalchemy.exc.SQLAlchemyError as sqlerr:
        raise ddserr.DatabaseError(message=sqlerr)

    # Check if the user and the deletion request exists
    if deletion_request_row:
        try:
            user = user_schemas.UserSchema().load({"email": email})
            _ = DBConnector.remove_user_self_deletion_request(user)
            DBConnector.delete_user(user)

        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise ddserr.UserDeletionError(
                message=f"User deletion request for {user.username} / {user.primary_email.email} failed due to database error: {sqlerr}",
                alt_message=f"Deletion request for user {user.username} registered with {user.primary_email.email} failed for technical reasons. Please contact the unit for technical support!",
            )

        flask.session.clear()

        return flask.make_response(
            flask.render_template("user/userdeleted.html", username=user.username, initial=True)
        )
    else:
        return flask.make_response(
            flask.render_template("user/userdeleted.html", username=email, initial=False)
        )
