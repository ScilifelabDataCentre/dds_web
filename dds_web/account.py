" Account info related endpoints "

from flask import Blueprint, render_template, request, current_app, session, redirect, url_for

from dds_web import timestamp
from dds_web.database import db_utils
from dds_web.utils import login_required

# temp will be removed in next version
from dds_web.development import cache_temp as tc

account_blueprint = Blueprint("account", __name__)

@account_blueprint.route("/<loginname>", methods=["GET"])
@login_required
def account_info(loginname=None):
    """account page"""
    #return session
    if session.get("is_admin"):
        return "admin"
        # return redirect(url_for("admin.admin_page"))
    if session["is_facility"]:
        return "facility"
        # projects_list = db_utils.get_facilty_projects(fid=session["facility_id"])
    else:
        return "other"
        # projects_list = db_utils.get_user_projects(uid=session["current_user_id"])
    # TO DO: change dbfunc passing in future
    # return render_template(
    #     "project/list_project.html",
    #     projects_list=projects_list,
    #     dbfunc=db_utils.get_facility_column,
    #     timestamp=timestamp,
    # )
