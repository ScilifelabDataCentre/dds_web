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

account_blueprint = Blueprint("account", __name__)


@account_blueprint.route("/<loginname>", methods=["GET"])
@login_required
def account_info(loginname=None):
    """account page"""
    account_info = {}
    # if session.get("is_admin"):
    #     if request.method == "GET":
    #         account_name = session["current_user"]
    #         account_name=db_utils.get_user_column_by_username(account_name, 'permissions')
    # if session["is_facility"]:
    #     if request.method == "GET":
    #         account_name = session["current_user"]
    #         account_name=db_utils.get_user_column_by_username(account_name, 'permissions')
    # elif session.get("current_user") and session.get("usid"):
    #     if request.method == "GET":
    #         account_name = session["current_user"]
    #         account_name=db_utils.get_user_column_by_username(account_name, 'permissions')
    if session.get("current_user"):
        if request.method == "GET":
            user = session["current_user"]
            account_info['username'] = user
            account_info['permissions'] = db_utils.get_user_column_by_username(user, "permissions")
            account_info['first_name'] = 'First'
            account_info['last_name'] = 'Last'
            account_info['email'] = ["userX@email1.com", "userX@email2.com"]

    return render_template(
        "account/account.html",
        enumerate=enumerate,
        account_info=account_info
    )
