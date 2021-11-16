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

# Own Modules
from dds_web import auth
from dds_web import forms
from dds_web.database import models

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
        return flask.redirect(flask.url_for("auth_blueprint.two_factor_setup"))

    # Go to login page if not authenticated
    return flask.redirect(flask.url_for("auth_blueprint.login"))


@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Log user in with DDS credentials."""
    # Redirect to index if user is already authenticated
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for("auth_blueprint.index"))
        # flask_login.logout_user()

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
        if not is_safe_url(next):
            return flask.abort(400)

        # Go to home page
        return flask.redirect(next or flask.url_for("auth_blueprint.index"))

    # Go to login form (get)
    return flask.render_template("user/login.html", form=form)


@auth_blueprint.route("/twofactor", methods=["GET"])
@flask_login.login_required
def two_factor_setup():
    """Setup two factor authentication."""

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
