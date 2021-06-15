
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
    test={
            "id": 1,
            "first_name": 'First',
            "last_name": 'Last',
            "username": 'username',
            "password": 'a',
            "settings": 'a',
            "email": ['userX@email1.com', 'userX@email2.com'],
            "phone": 'a',
            "admin": 'a'
        }
    if session.get("is_admin"):
        test_get=["test"]
    if session["is_facility"]:
        # test_get=["test"]
        # projects_list = db_utils.get_facilty_projects(fid=session["facility_id"])
        if request.method == "GET":
            account_name = request.form.get("account_name")
            # user_role=db_utils.get_facility_column_by_username(account_name, "public_id")
    else:
        # test_get = db_utils.get_user_projects(uid=session["current_user_id"])
        # test_get=db_utils.get_user_column_by_username(username=session["current_user_id"], column='role')
        if request.method == "GET":
            account_name = request.form.get("account_name")
            # user_role=db_utils.get_user_column_by_username(account_name, "public_id")

    return render_template("account/account.html",
                            enumerate=enumerate,
                            test=test,
                            test_get=account_name)