""""""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import io
import json
import os

# Installed
import flask
import werkzeug
from dds_web.api.db_connector import DBConnector
import flask_login
import flask_mail
import pyqrcode
import pyotp
import itsdangerous
import sqlalchemy
import marshmallow
from cryptography.hazmat.primitives.twofactor.hotp import HOTP
from cryptography.hazmat.primitives.hashes import SHA512

# Own Modules
from dds_web import auth
from dds_web import forms
from dds_web.database import models
import dds_web.utils
from dds_web import db, limiter
import dds_web.errors as ddserr
from dds_web.api.schemas import user_schemas
from dds_web import mail


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
    error_message=ddserr.error_codes["TooManyRequestsError"]["message"],
)
def confirm_invite(token):
    """Confirm invitation."""
    s = itsdangerous.URLSafeTimedSerializer(flask.current_app.config.get("SECRET_KEY"))

    try:
        # Get email from token
        email = s.loads(token, salt="email-confirm", max_age=604800)

        # Get row from invite table
        invite_row = models.Invite.query.filter(models.Invite.email == email).first()

    except itsdangerous.exc.SignatureExpired as signerr:
        db.session.delete(invite_row)
        db.session.commit()
        raise  # TODO: Do not raise api error here, should fix new error handling for web page
    except (itsdangerous.exc.BadSignature, itsdangerous.exc.BadTimeSignature) as badsignerr:
        raise
    except sqlalchemy.exc.SQLAlchemyError as sqlerr:
        raise

    # Check the invite exists
    if not invite_row:
        if dds_web.utils.email_in_db(email=email):
            return flask.make_response(flask.render_template("user/userexists.html"))
        else:
            raise ddserr.InviteError(
                message=f"There is no pending invitation for the email adress: {email}"
            )

    # Initiate form if the invite exists
    form = forms.RegistrationForm()
    # invite columns: unit_id, email, role

    # Prefill fields - facility readonly if filled, otherwise disabled
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
    error_message=ddserr.error_codes["TooManyRequestsError"]["message"],
)
def register():
    """Handles the creation of a new user"""
    form = dds_web.forms.RegistrationForm()

    # Validate form - validators defined in form class
    if form.validate_on_submit():
        # Create new user row by loading form data into schema
        try:
            new_user = user_schemas.NewUserSchema().load(form.data)

        except marshmallow.ValidationError as valerr:
            flask.current_app.logger.warning(valerr)
            raise
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.IntegrityError) as sqlerr:
            raise ddserr.DatabaseError from sqlerr

    # Go to registration form
    return flask.render_template("user/register.html", form=form)


@auth_blueprint.route("/request_2fa", methods=["GET", "POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    methods=["POST"],
    error_message=ddserr.error_codes["TooManyRequestsError"]["message"],
)
def request_2fa():
    """Request a HOTP (authentication one-time token) to be sent to your email"""
    if flask.request.method == "GET":
        form = forms.Request2FAForm()
        return flask.render_template("user/request2fa.html", form=form)
    elif flask.request.method == "POST":
        form = forms.Request2FAForm()
        if form.validate_on_submit():
            # Get user from database
            user = models.User.query.get(form.username.data)

            # incorrect credentials
            if not user or not user.verify_password(input_password=form.password.data):
                flask.flash("Invalid username or password.")
                return flask.redirect(
                    flask.url_for("auth_blueprint.request_2fa", next=next)
                )  # Try again

            # Generate HOTP token
            hotp_value = user.generate_HOTP_token()

            msg = dds_web.utils.create_one_time_password_email(user, hotp_value)

            mail.send(msg)

            flask.flash("One-Time Code sent to your email.")
            return flask.redirect(flask.url_for("auth_blueprint.login"))
        else:
            return flask.render_template("user/request2fa.html", form=form)


@auth_blueprint.route("/login", methods=["GET", "POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    methods=["POST"],
    error_message=ddserr.error_codes["TooManyRequestsError"]["message"],
)
def login():
    """Log user in with DDS credentials."""

    # Redirect to index if user is already authenticated
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for("auth_blueprint.index"))

    next = flask.request.args.get("next")
    # is_safe_url should check if the url is safe for redirects.
    if not dds_web.utils.is_safe_url(next):
        return flask.abort(400)

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

        hotp_value = form.hotp.data
        # Raises authenticationerror if invalid
        try:
            user.verify_HOTP(hotp_value.encode())
        except ddserr.AuthenticationError:
            flask.flash("Invalid one-time code.")
            return flask.redirect(flask.url_for("auth_blueprint.login", next=next))

        # Correct username, password and hotp code --> log user in
        flask_login.login_user(user)
        flask.flash("Logged in successfully.")

        # Go to home page
        return flask.redirect(next or flask.url_for("auth_blueprint.index"))

    # Go to login form (get)
    return flask.render_template("user/login.html", form=form, next=next)


@auth_blueprint.route("/logout", methods=["POST"])
@flask_login.login_required
def logout():
    """Logout user."""

    if flask_login.current_user.is_authenticated:
        flask_login.logout_user()

    return flask.redirect(flask.url_for("auth_blueprint.index"))


@auth_blueprint.route("/reset_password", methods=["GET", "POST"])
@limiter.limit(
    dds_web.utils.rate_limit_from_config,
    methods=["POST"],
    error_message=ddserr.error_codes["TooManyRequestsError"]["message"],
)
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
    error_message=ddserr.error_codes["TooManyRequestsError"]["message"],
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
def confirm_self_deletion(token):
    """Confirm user deletion."""
    s = itsdangerous.URLSafeTimedSerializer(flask.current_app.config.get("SECRET_KEY"))

    try:
        # Get email from token
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
        db.session.delete(
            models.DeletionRequest.query.filter(models.DeletionRequest.email == email).all()
        )
        db.session.commit()
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
            DBConnector.delete_user(user)

            # remove the deletion request from the database
            db.session.delete(deletion_request_row)
            db.session.commit()

        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise ddserr.UserDeletionError(
                message=f"User deletion request for {user.username} / {user.primary_email.email} failed due to database error: {sqlerr}",
                alt_message=f"Deletion request for user {user.username} registered with {user.primary_email.email} failed for technical reasons. Please contact the unit for technical support!",
            )

        return flask.make_response(
            flask.render_template("user/userdeleted.html", username=user.username, initial=True)
        )
    else:
        return flask.make_response(
            flask.render_template("user/userdeleted.html", username=email, initial=False)
        )
