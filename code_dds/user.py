"User display and login/logout HTMl endpoints."

from flask import (Blueprint, render_template, request,
                   session, redirect, url_for)

from code_dds.api.login import ds_access
from code_dds.crypt.auth import validate_user_credentials
from code_dds.db_code import models
from code_dds.db_code import db_utils
from code_dds.db_code import marshmallows as marmal
from code_dds.utils import login_required

user_blueprint = Blueprint("user", __name__)


@user_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Login to a user account"""

    if request.method == "GET":
        if session.get('current_user'):
            return redirect(url_for('user.user_page', loginname=session['current_user']))
        else:
            return render_template('user/login.html', next=request.args.get('next'))
        
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        credentials_validated, is_facility, message, user_info = validate_user_credentials(username, password)
        if not credentials_validated:
            return render_template('user/login.html', next=request.form.get('next'), login_error_message=message)
        session['current_user'] = user_info['username']
        session['current_user_id'] = user_info['id']
        session['is_facility'] = is_facility
        session['facility_name'] = user_info.get('facility_name')
        if request.form.get('next'):
            to_go_url = request.form.get('next')
        else:
            to_go_url = url_for('user.user_page', loginname=request.form.get('username'))    
        return redirect(to_go_url)


@user_blueprint.route("/logout", methods=["GET"])
def logout():
    """Logout of a user account"""
    session.pop('current_user', None)
    session.pop('current_user_id', None)
    session.pop('is_facility', None)
    session.pop('facility_name', None)
    return redirect(url_for('home'))


@user_blueprint.route("/<loginname>", methods=["GET"])
@login_required
def user_page(loginname=None):
    """User home page"""
    
    if session['is_facility']:
        projects_list = models.Project.query.filter_by(facility=session['current_user_id']).all()
    else:
        projects_list = models.Project.query.filter_by(owner=session['current_user_id']).all()
    return render_template('project/list_project.html', projects_list=projects_list)


# @user_blueprint.route("/signup", methods=["GET", "POST"])
# def signup():
#     """Signup a user account"""
#
#     if request.method == "GET":
#         return render_template('user/signup.html', title='Signup')
#     if request.method == "POST":
#         pass