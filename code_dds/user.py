"User display and login/logout HTMl endpoints."

import http.client
import json
import re

from flask import (Blueprint, render_template,
                   request, session, redirect, url_for, g, current_app)
# import flask_mail
from werkzeug.security import check_password_hash, generate_password_hash

from code_dds.api.login import ds_access

#from code_dds import utils

KEYS = ["ID", "Firstname", "Lastname", "Username", "Password", "Settings",
        "Email", "Phone"]

user_blueprint = Blueprint("user", __name__, url_prefix="/user")


@user_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Login to a user account"""

    if request.method == "GET":
        return render_template('user/login.html')
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        role = 'facility' if request.form.get('facility') == 'on' else 'user'
        valid_user, user_id, message = ds_access(username, password, role)
        if valid_user:
            session['current_user'] = "username1"
            session['modified'] = True
            return redirect(url_for('user.userhome'))
        else:
            raise ValueError


@user_blueprint.route("/logout", methods=["GET"])
def logout():
    """Logout of a user account"""
    session.pop('current_user', None)
    return redirect(url_for('home'))

@user_blueprint.route("/userhome", methods=["GET"])
def userhome():
    """User home page"""
    from code_dds.development.dds_mock_data import projects_list
    return render_template('project/list_project.html', projects_list=projects_list)


@user_blueprint.route("/signup", methods=["GET", "POST"])
def signup():
    """Signup a user account"""

    if request.method == "GET":
        return render_template('user/signup.html', title='Signup')
    if request.method == "POST":
        pass