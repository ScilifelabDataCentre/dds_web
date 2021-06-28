from flask import Blueprint, render_template, request, current_app, session, redirect, url_for

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

    username=session["current_user"]

    account_info = {}
    account_info['username'] = username
    account_info['permissions'] = db_utils.get_user_column_by_username(username, 'permissions')
    account_info['first_name'] = None #db_utils.get_user_column_by_username(username, 'first_name')
    account_info['last_name'] =  None #db_utils.get_user_column_by_username(username, 'last_name')

    user_info_list = models.User.query.filter_by(username=username).all()
    account_info["emails"] = [
        {'address': getattr(user_row, "email", None),
        'primary': getattr(user_row, "primary", False)}
        for user_row in user_info_list
    ]
    account_info["emails"] = sorted(account_info["emails"],
                                    key=lambda k: k['primary'],
                                    reverse=True)

    return account_info

# @account_blueprint.route("/test")
# def account_test(loginname=None):
#     """account page"""

#     username=session["current_user"]

#     account_info = {
#             'username': username,
#             'emails': [], #[{"address": "userX@email1.com", "primary": False}, {"address": "userX@email2.com", "primary": True}]
#             'permissions': None,
#             'first_name': None,
#             'last_name': None
#         }

#     for info in account_info:
#         if info != "username" or info !="emails":
#             try:
#                 # TO DO: change to db.one_or_none()
#                 account_info[info] = db_utils.get_user_column_by_username(username, info)
#             except:
#                 pass
#         if info == "emails":
#             user_info_list = models.User.query.filter_by(username=username).all()
#             account_info["emails"] = [
#                 {'address': getattr(user_row, "email", None),
#                 'primary': getattr(user_row, "primary", False)}
#                 for user_row in user_info_list
#             ]

#     account_info["emails"] = sorted(account_info["emails"],
#                                     key=lambda k: k['primary'],
#                                     reverse=True)
#     # TO DO:
#     # GET info
#     # POST new email
#     # DELETE email
#     # PUT update name

#     return json.dumps(account_info)