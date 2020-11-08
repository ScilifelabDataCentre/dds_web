" Project info related endpoints "

from flask import (Blueprint, render_template, request,
                   session, redirect, url_for)

project_blueprint = Blueprint("project", __name__, url_prefix="/project")

@user_blueprint.route("/<project_id>", methods=["GET"])
def project_info():
    """Logout of a user account"""
    session.pop('current_user', None)
    return redirect(url_for('home'))
