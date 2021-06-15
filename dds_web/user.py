"User display and login/logout HTMl endpoints."

from flask import Blueprint, render_template, request, current_app, session, redirect, url_for

from dds_web import timestamp
from dds_web.api.login import ds_access
from dds_web.crypt.auth import validate_user_credentials
from dds_web.database import models
from dds_web.database import db_utils
from dds_web.utils import login_required


from dds_web import db


# temp will be removed in next version
from dds_web.development import cache_temp as tc

user_blueprint = Blueprint("user", __name__)


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
    #return session
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
