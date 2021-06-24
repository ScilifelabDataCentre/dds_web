from flask import Blueprint, render_template, request, current_app, session, redirect, url_for,json

from dds_web import timestamp
from dds_web.api.login import ds_access
from dds_web.crypt.auth import validate_user_credentials
from dds_web.database import models
from dds_web.database import db_utils
from dds_web.utils import login_required

# temp will be removed in next version
from dds_web.development import cache_temp as tc

account_blueprint = Blueprint("account", __name__)


@account_blueprint.route("/<loginname>", methods=["GET", "POST"])
@login_required
def account_info(loginname=None):
    """account page"""

    return render_template("account/account.html")

@account_blueprint.route("/test")
def account_test(loginname=None):
    """account page"""

    user=session["current_user"]

    account_info = {
            'username': user,
            'emails': [ {'address':'test@example.com', 'primary': False},
            {'address':'test2@example.com', 'primary': True}],
            'permissions': None,
            'first_name': None,
            'last_name': None
        }

    for info in account_info:
        if info != "username" or info !="emails":
            try:
                account_info[info] = db_utils.get_user_column_by_username(user, info)
            except:
                pass
        if info == "emails":
            pass

    # account_info = {
    #         'username': user,
    #         'emails': [ {'address':'test@example.com', 'primary': False},
    #         {'address':'test2@example.com', 'primary': True}],
    #         'permissions': db_utils.get_user_column_by_username(user, "permissions"),
    #         'first_name': 'test',
    #         'last_name': 'tester'
    #     }

    account_info["emails"] = sorted(account_info["emails"], key=lambda k: k['primary'], reverse=True)

    return json.dumps(account_info)

    # if session.get("current_user"):
    #     if request.method == "GET":
    #         user = session["current_user"]
    #         account_info["username"] = user
    #         account_info["permissions"] = db_utils.get_user_column_by_username(user, "permissions")
    #         account_info["first_name"] = "First"
    #         account_info["last_name"] = "Last"
    #         account_info["email"] = [{"address": "userX@email1.com", "primary": False}, {"address": "userX@email2.com", "primary": True}]
    #         account_info["emails"] = sorted(account_info["emails"], key=lambda k: k['primary'], reverse=True)

    #     if request.method == "POST":
    #         pass
    #         # username = request.form.get("username")
    #         # password = request.form.get("password")