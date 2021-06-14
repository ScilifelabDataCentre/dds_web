"User display and login/logout HTMl endpoints."

import flask
from flask import render_template, request, current_app, session, redirect, url_for
import sqlalchemy

from dds_web import timestamp, oauth
from dds_web.api.login import ds_access
from dds_web.crypt.auth import validate_user_credentials
from dds_web.database import models
from dds_web.database import db_utils
from dds_web.utils import login_required

# temp will be removed in next version
from dds_web.development import cache_temp as tc

user_blueprint = flask.Blueprint("user", __name__)


@user_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Login to a user account"""

    if request.method == "GET":
        if session.get("is_admin"):
            return redirect(url_for("admin.admin_page"))
        elif session.get("current_user") and session.get("usid"):
            return redirect(url_for("user.user_page", loginname=session["current_user"]))
        else:
            return render_template("user/login.html", next=request.args.get("next"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        credentials_validated, is_facility, message, user_info = validate_user_credentials(
            username, password
        )
        if not credentials_validated:
            return render_template(
                "user/login.html", next=request.form.get("next"), login_error_message=message
            )
        session["current_user"] = user_info["username"]
        session["current_user_id"] = user_info["id"]
        session["is_admin"] = user_info.get("admin", False)
        session["is_facility"] = is_facility
        session["facility_name"] = user_info.get("facility_name")
        session["facility_id"] = user_info.get("facility_id")
        # temp admin fix
        if session["is_admin"]:
            return redirect(url_for("admin.admin_page"))
        # temp should be removed in next version
        import os

        usid = os.urandom(3).hex()
        session["usid"] = usid
        tc.store_temp_ucache(username, password, usid)
        if request.form.get("next"):
            to_go_url = request.form.get("next")
        else:
            to_go_url = url_for("user.user_page", loginname=request.form.get("username"))
        return redirect(to_go_url)


def do_login(session, identifier: str, password: str = "") -> bool:
    """
    Check if a user with matching identifier exists. If so, log in as that user.

    TODO:
      * Add support for passwords

    Args:
        session: The Flask session to use.
        identifer (str): User identifier to use for login.
        password (str): Password in case a password is used for the login.

    Returns:
        bool: Whether the login attempt succeeded.
    """
    try:
        account = models.Identifier.query.filter(models.Identifier.identifier == identifier).first()
    except sqlalchemy.exc.SQLAlchemyError:
        return False
    user_info = account.user
    # Use the current login definitions for compatibility
    session["current_user"] = user_info.username
    session["current_user_id"] = user_info.id
    session["is_admin"] = user_info.role == "admin"
    session["is_facility"] = user_info.role == "facility"
    if session["is_facility"]:
        facility_info = models.Facility.query.filter(
            models.Facility.id == account.facility_id
        ).first()

        session["facility_name"] = facility_info.name
        session["facility_id"] = facility_info.id
    return True


@user_blueprint.route("/login-oidc")
def oidc_login():
    """Perform a login using OpenID Connect (e.g. Elixir AAI)."""
    client = oauth.create_client("default_login")
    if not client:
        return flask.Response(status=404)
    redirect_uri = flask.url_for("user.oidc_authorize", _external=True)
    return client.authorize_redirect(redirect_uri)


@user_blueprint.route("/login-oidc/authorize")
def oidc_authorize():
    """Authorize a login using OpenID Connect (e.g. Elixir AAI)."""
    client = oauth.create_client("default_login")
    token = client.authorize_access_token()
    if "id_token" in token:
        user_info = client.parse_id_token(token)
    else:
        user_info = client.userinfo()

    if do_login(flask.session, user_info["email"]):
        flask.current_app.logger.info(f"Passed login attempt")
        return flask.redirect(flask.url_for("home"))
    else:
        return flask.abort(status=403)


@user_blueprint.route("/logout", methods=["GET"])
def logout():
    """Logout of a user account"""
    # temp should be removed in next version
    tc.clear_temp_ucache(session.get("current_user"), session.get("usid"))
    session.pop("current_user", None)
    session.pop("current_user_id", None)
    session.pop("is_facility", None)
    session.pop("is_admin", None)
    session.pop("facility_name", None)
    session.pop("facility_id", None)
    session.pop("usid", None)
    return redirect(url_for("home"))


@user_blueprint.route("/<loginname>", methods=["GET"])
@login_required
def user_page(loginname=None):
    """User home page"""
    # return session
    if session.get("is_admin"):
        return redirect(url_for("admin.admin_page"))
    if session["is_facility"]:
        projects_list = db_utils.get_facilty_projects(fid=session["facility_id"])
    else:
        projects_list = db_utils.get_user_projects(uid=session["current_user_id"])
    # TO DO: change dbfunc passing in future
    return render_template(
        "project/list_project.html",
        projects_list=projects_list,
        dbfunc=db_utils.get_facility_column,
        timestamp=timestamp,
    )


# @user_blueprint.route("/signup", methods=["GET", "POST"])
# def signup():
#     """Signup a user account"""
#
#     if request.method == "GET":
#         return render_template('user/signup.html', title='Signup')
#     if request.method == "POST":
#         pass
