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
        return flask.redirect(next or flask.url_for("auth_blueprint.index"))

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


@auth_blueprint.route("/twofa", methods=["GET"])
@flask_login.login_required
def setup_2fa():
    """Send and validate two factor authentication."""

    # TODO
    # 1. Get secret from user table
    flask.current_app.logger.debug("user hotp secret: {auth.current_user}")

    # 2. Generate HOTP and save counter
    # 3. Generate email
    # 4. Redirect to 2fa form
    # 5. Validate
    # 6. Redirect

    return
