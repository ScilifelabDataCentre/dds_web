" Project info related endpoints "

import os

from random import randrange
from flask import (Blueprint, render_template, request, current_app,
                   session, redirect, url_for, g, flash)

from code_dds import db
from code_dds.db_code import models
from code_dds.db_code import db_utils
from code_dds.db_code import marshmallows as marmal
from code_dds.crypt.key_gen import project_keygen
from code_dds.utils import login_required, get_timestamp
from werkzeug.utils import secure_filename
project_blueprint = Blueprint("project", __name__)


@project_blueprint.route("/add_project", methods=["GET", "POST"])
@login_required
def add_project():
    """ Add new project to the database """
    if request.method == "GET":
        return render_template("project/add_project.html")
    if request.method == "POST":
        # Check no empty field from form
        for k in ['title', 'owner', 'description']:
            if not request.form.get(k):
                return render_template("project/add_project.html",
                                       error_message="Field '{}' should not be empty".format(k))

        # Check if the user actually exists
        if request.form.get('owner') not in db_utils.get_full_column_from_table(table='User', column='username'):
            return render_template("project/add_project.html",
                                   error_message="Given username '{}' does not exist".format(request.form.get('owner')))

        project_inst = create_project_instance(request.form)
        # This part should be moved elsewhere to dedicated DB handling script
        new_project = models.Project(**project_inst.project_info)
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('project.project_info', project_id=new_project.id))


@project_blueprint.route("/<project_id>", methods=["GET"])
@login_required
def project_info(project_id=None):
    """Get the given project's info"""

    files_list = models.File.query.filter_by(project_id=project_id).all()
    if files_list:
        uploaded_data = folder(files_list).generate_html_string()
    else:
        uploaded_data = None
    project_info = models.Project.query.filter_by(id=project_id).first()
    return render_template("project/project.html", project=project_info, uploaded_data=uploaded_data)


@project_blueprint.route("upload", methods=["POST"])
@login_required
def data_upload():
    project_id = request.args.get('project_id', None)
    if project_id is None:
        msg = "No project id provided"
        return("No project id {}".format(project_id))
    elif 'files' not in request.files:
        msg = "No file part available"
        return(request.form)
    elif request.files['files'].filename == '':
        msg = "No file uploaded"
        return("No file selected")
    elif request.files['files']:
        in_files = request.files.getlist('files')
        upload_file_dest = os.path.join(current_app.config['UPLOAD_FOLDER'], "{}_T{}".format(project_id, get_timestamp(tformat="%y%m%d%H%M%S%f")))
        os.mkdir(upload_file_dest)
        for in_file in in_files:
            file_target_path = upload_file_dest
            path_splitted = in_file.filename.split("/")
            filename = secure_filename(path_splitted[-1])
            if len(path_splitted) > 1:
                for p in path_splitted[:-1]:
                    file_target_path = os.path.join(file_target_path, p)
                    if not os.path.exists(file_target_path):
                        os.mkdir(file_target_path)
            in_file.save(os.path.join(file_target_path, filename))
        msg = "Files uploaded"
        return("Files uploaded")
    #return redirect(request.url)

########## HELPER CLASSES AND FUNCTIONS ##########


class create_project_instance(object):
    """ Creates a project instance to add in DB"""

    def __init__(self, project_info):
        self.project_info = {
            'id': self.get_new_id(),
            'title': project_info['title'],
            'description': project_info['description'],
            'owner': project_info['owner'],
            'category': 'alphatest',
            'sensitive': False,
            'delivery_option': 'S3',
            'facility': g.current_user_id,
            'status': 'In facility',
            'order_date': get_timestamp(tformat="%Y-%m-%d"),
            'pi': 'NA',
            'size': 0,
            'size_enc': 0,
            'delivery_date': None
        }
        pkg = project_keygen(self.project_info['id'])
        self.project_info.update(pkg.get_key_info_dict())

    def get_new_id(self, id=None):
        facility_ref = db_utils.get_facility_column(
            fid=session.get('current_user_id'), column='internal_ref')
        new_id = "{}{:3}".format(facility_ref, randrange(1, 10**3))
        while not self.__is_column_value_uniq(table='Project', column='id', value=new_id):
            new_id = "{}{:3}".format(facility_ref, randrange(1, 10**3))
        return new_id

    def __is_column_value_uniq(self, table, column, value):
        """ See that the value is unique in DB """
        all_column_values = db_utils.get_full_column_from_table(table=table, column=column)
        return value not in all_column_values


class folder(object):
    """ A class to parse the file list and do appropriate ops """

    def __init__(self, file_list):
        self.files = file_list
        self.files_arranged = {}

    def arrange_files(self):
        """ Method to arrange files that reflects folder structure """
        for _file in self.files:
            self.__parse_and_put_file(
                _file.name, _file.size, self.files_arranged)

    def generate_html_string(self, arrange=True):
        """ Generates html string for the files to pass in template """
        if arrange and not self.files_arranged:
            self.arrange_files()

        return self.__make_html_string_from_file_dict(self.files_arranged)

    def __parse_and_put_file(self, file_name, file_size, target_dict):
        """ Private method that actually """
        file_name_splitted = file_name.split('/', 1)
        if len(file_name_splitted) == 2:
            parent_dir, remaining_file_path = file_name_splitted
            if parent_dir not in target_dict:
                target_dict[parent_dir] = {}
            self.__parse_and_put_file(
                remaining_file_path, file_size, target_dict[parent_dir])
        else:
            target_dict[file_name] = file_size

    def __make_html_string_from_file_dict(self, file_dict):
        """ Takes a dict with files and creates html string with <ol> tag """
        _html_string = ""
        for _key, _value in file_dict.items():
            if isinstance(_value, dict):
                div_id = "d{}".format(get_timestamp(tformat="%y%m%d%H%M%S%f"))
                _html_string += ("<li> <a class='folder' data-toggle='collapse' href='#{did}' aria-expanded='false' aria-controls='{did}'>{_k}</a> "
                                 "<div class='collapse' id='{did}'>{_v}</div> "
                                 "</li>").format(did=div_id, _k=_key, 
                                 _v=self.__make_html_string_from_file_dict(_value))
            else:
                _html_string += "<li><div class='hovertip'>{_k} <span class='hovertiptext'> {_v}Kb </span></div></li>".format(_k=_key, _v=_value)
        return '<ul style="list-style: none;"> {} </ul>'.format(_html_string)
