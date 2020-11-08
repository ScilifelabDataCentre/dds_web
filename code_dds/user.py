"User display and login/logout HTMl endpoints."

from flask import (Blueprint, render_template, request,
                   session, redirect, url_for)

from code_dds.api.login import ds_access
from code_dds import models
from code_dds import marshmallows as marmal
from code_dds.utils import login_required

user_blueprint = Blueprint("user", __name__)


@user_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Login to a user account"""

    if request.method == "GET":
        return render_template('user/login.html', next=request.args.get('next'))
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        role = 'facility' if request.form.get('facility') == 'on' else 'user'
        valid_user, user_id, message = ds_access(username, password, role)
        if valid_user:
            session['current_user'] = "username1"
            session['modified'] = True
            if request.form.get('next'):
                to_go_url = request.form.get('next')
            else:
                to_go_url = url_for('home')
            return redirect(to_go_url)
        else:
            raise ValueError


@user_blueprint.route("/logout", methods=["GET"])
def logout():
    """Logout of a user account"""
    session.pop('current_user', None)
    return redirect(url_for('home'))


@user_blueprint.route("/<username>", methods=["GET"])
@login_required
def user_page(username=None):
    """User home page"""
    
    projects_list = models.Project.query.filter_by(owner=username).all()
    return render_template('project/list_project.html', projects_list=projects_list)


# @user_blueprint.route("/signup", methods=["GET", "POST"])
# def signup():
#     """Signup a user account"""
#
#     if request.method == "GET":
#         return render_template('user/signup.html', title='Signup')
#     if request.method == "POST":
#         pass