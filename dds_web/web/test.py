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

# Own Modules
from dds_web import auth
from dds_web import forms
from dds_web.database import models
import dds_web.utils

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################
auth_blueprint = flask.Blueprint("auth_blueprint", __name__)


@auth_blueprint.route("/", methods=["GET"])
def index():
    """DDS start page."""
    # Check if user has 2fa setup
    if flask_login.current_user.is_authenticated:
        # TODO: Check if user has 2fa set up -> if not setup, if yes go to index.
        return flask.redirect(
            flask.url_for("auth_blueprint.two_factor_setup"),
        )

    # Go to login page if not authenticated
    return flask.redirect(flask.url_for("auth_blueprint.login"))


@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Log user in with DDS credentials."""
    # Redirect to index if user is already authenticated
    if flask_login.current_user.is_authenticated:
        # return flask.redirect(flask.url_for("auth_blueprint.index"))
        flask_login.logout_user()

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


@auth_blueprint.route("/twofactor", methods=["GET"])
@flask_login.login_required
def two_factor_setup():
    """Setup two factor authentication."""

    # since this page contains the sensitive qrcode, make sure the browser
    # does not cache it
    return (
        flask.render_template(
            "user/two-factor-setup.html", secret=flask_login.current_user.otp_secret
        ),
        200,
        {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@auth_blueprint.route("/twofactor/verify", methods=["POST"])
@flask_login.login_required
def two_factor_verify():
    """Verify two factor authentication."""

    otp = int(flask.request.form.get("otp"))
    if pyotp.TOTP(flask_login.current_user.otp_secret).verify(otp):
        flask.flash("The TOTP 2FA token is valid", "success")
        return "ok"
    else:
        flask.flash("You have supplied an invalid 2FA token!", "danger")
        return "fail"


@auth_blueprint.route("/qrcode", methods=["GET"])
@flask_login.login_required
def qrcode():
    """Generate qrcode"""
    # render qrcode for FreeTOTP
    url = pyqrcode.create(flask_login.current_user.totp_uri())
    stream = io.BytesIO()
    url.svg(stream, scale=5)
    return (
        stream.getvalue(),
        200,
        {
            "Content-Type": "image/svg+xml",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
