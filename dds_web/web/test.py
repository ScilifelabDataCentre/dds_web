import io
import flask
import flask_login
from dds_web import auth
from dds_web import forms
from dds_web.database import models
import urllib.parse
import pyqrcode

web_blueprint = flask.Blueprint("web_blueprint", __name__)


def is_safe_url(target):
    """Check if the url is safe for redirects."""
    ref_url = urllib.parse.urlparse(flask.request.host_url)
    test_url = urllib.parse.urlparse(urllib.parse.urljoin(flask.request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@web_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""
    # Redirect to index if user is already authenticated
    if flask_login.current_user.is_authenticated:
        # return flask.redirect(flask.url_for("web_blueprint.index"))
        flask_login.logout_user()

    # Check if for is filled in (correctly)
    form = forms.LoginForm()
    if form.validate_on_submit():
        user = models.User.query.get(form.username.data)

        # Unsuccessful login
        if not user or not user.verify_password(input_password=form.password.data):
            flask.flash("Invalid username or password.")
            return flask.redirect(flask.url_for("web_blueprint.login"))

        # Correct username and password --> log user in
        flask_login.login_user(user)
        flask.flash("Logged in successfully.")

        next = flask.request.args.get("next")
        # is_safe_url should check if the url is safe for redirects.
        if not is_safe_url(next):
            return flask.abort(400)

        return flask.redirect(next or flask.url_for("web_blueprint.index"))

    # Go to login form
    return flask.render_template("user/login.html", form=form)


@web_blueprint.route("/", methods=["GET"])
def index():
    """ """

    # Check if user has 2fa setup
    if flask_login.current_user.is_authenticated:
        if flask_login.current_user.otp_secret:
            return flask.redirect(flask.url_for("web_blueprint.two_factor_setup"))

    # If not - go to setup
    # If yes - go to home page

    return "test"


@web_blueprint.route("/twofactor", methods=["GET"])
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
