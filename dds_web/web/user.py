""""""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import io

# Installed
import flask
import flask_login
import pyqrcode
import pyotp
import itsdangerous
import sqlalchemy
import marshmallow


# Own Modules
from dds_web import auth
from dds_web import forms
from dds_web.database import models
import dds_web.utils
from dds_web import db
import dds_web.api.errors as ddserr
from dds_web.api.schemas import user_schemas
from dds_web import mail
import flask_mail


####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################
auth_blueprint = flask.Blueprint("auth_blueprint", __name__)


@auth_blueprint.route("/", methods=["GET"])
@flask_login.login_required
def index():
    """DDS start page."""
    form = forms.LogoutForm()
    return flask.render_template("index.html", form=form)


@auth_blueprint.route("/confirm_invite/<token>", methods=["GET"])
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

    # Initiate form
    form = forms.RegistrationForm()

    # invite columns: unit_id, email, role
    flask.current_app.logger.debug(invite_row)

    # Prefill fields - facility readonly if filled, otherwise disabled
    form.unit_name.render_kw = {"disabled": True}
    if invite_row.unit:  # backref to unit
        form.unit_name.data = invite_row.unit.name
        form.unit_name.render_kw = {"readonly": True}

    form.email.data = email
    form.username.data = email.split("@")[0]

    return flask.render_template("user/register.html", form=form)


@auth_blueprint.route("/register", methods=["POST"])
def register():
    """Handles the creation of a new user"""
    form = dds_web.forms.RegistrationForm()

    # Validate form - validators defined in form class
    if form.validate_on_submit():
        # Create new user row by loading form data into schema
        try:
            new_user = user_schemas.NewUserSchema().load(form.data)

        except marshmallow.ValidationError as valerr:
            flask.current_app.logger.info(valerr)
            raise
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.IntegrityError) as sqlerr:
            raise ddserr.DatabaseError from sqlerr

        # Go to two factor authentication setup
        return flask.redirect(flask.url_for("auth_blueprint.setup_2fa"))

    # Go to registration form
    return flask.render_template("user/register.html", form=form)


@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Log user in with DDS credentials."""

    # Redirect to index if user is already authenticated
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for("auth_blueprint.index"))

    # Check if for is filled in and correctly (post)
    form = forms.LoginForm()
    if form.validate_on_submit():
        # Get user from database
        user = models.User.query.get(form.username.data)

        # Unsuccessful login
        if not user or not user.verify_password(input_password=form.password.data):
            flask.flash("Invalid username or password.")
            return flask.redirect(flask.url_for("auth_blueprint.login"))  # Try login again

        # Correct username and password --> log user in
        flask_login.login_user(user)
        flask.flash("Logged in successfully.")

        next = flask.request.args.get("next")
        # is_safe_url should check if the url is safe for redirects.
        if not dds_web.utils.is_safe_url(next):
            return flask.abort(400)

        # Go to home page
        return flask.redirect(next or flask.url_for("auth_blueprint.auth_2fa"))

    # Go to login form (get)
    return flask.render_template("user/login.html", form=form)


@auth_blueprint.route("/logout", methods=["POST"])
def logout():
    """Logout user."""

    if flask_login.current_user.is_authenticated:
        flask_login.logout_user()

    return flask.redirect(flask.url_for("auth_blueprint.index"))


@auth_blueprint.route("/reset_password", methods=["GET", "POST"])
def request_reset_password():
    """Request to reset password."""
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
def reset_password(token):
    """Perform the password reset."""
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


@auth_blueprint.route("/2fa", methods=["GET", "POST"])
@flask_login.login_required
def auth_2fa():
    """Send and validate two factor authentication."""

    # TODO
    from cryptography.hazmat.primitives.twofactor.hotp import HOTP
    from cryptography.hazmat.primitives.hashes import SHA512

    if flask.request.method == "GET":
        hotp = HOTP(flask_login.current_user.hotp_secret, 8, SHA512())

        # 1. Get secret from user table
        flask.current_app.logger.debug(f"user hotp secret: {flask_login.current_user.hotp_secret}")

        # 2. Generate HOTP and save counter
        counter = 0
        hotp_value = hotp.generate(counter=counter)
        flask.current_app.logger.debug(f"hotp value: {hotp_value}")

        # 3. Generate email
        # flask_login.current_user.primary_email
        message = flask_mail.Message(
            "One-Time Code",
            sender=flask.current_app.config.get("MAIL_SENDER", "dds@noreply.se"),
            recipients=[flask_login.current_user.primary_email],
        )
        message.body = f"One time code for DDS authentication: {hotp_value}"
        mail.send(message)

        # 4. Redirect to 2fa form
        # 5. Validate
        # hotp.verify(hotp_value, 4)

        # 6. Redirect
        form = forms.TwoFactorAuthForm()
        return flask.render_template("user/2fa.html", form=form)
    elif flask.request.method == "POST":
        return flask.redirect(flask.url_for("auth_blueprint.index"))
