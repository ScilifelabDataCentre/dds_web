" Project info related endpoints "

from flask import (Blueprint, render_template, request,
                   session, redirect, url_for)

from code_dds import models
from code_dds import marshmallows as marmal
from code_dds.utils import login_required

project_blueprint = Blueprint("project", __name__)

@project_blueprint.route("/<project_id>", methods=["GET"])
@login_required
def project_info(project_id=None):
    """Get the given project's info"""
    
    project_info = models.Project.query.filter_by(id=project_id).first()    
    return render_template("project/project.html", project=project_info)
