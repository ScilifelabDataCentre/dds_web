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
    
    files_list = models.File.query.filter_by(project_id=project_id).all()
    if files_list:
        uploaded_data = folder(files_list).generate_html_string()
    else:
        uploaded_data = None
    project_info = models.Project.query.filter_by(id=project_id).first()    
    return render_template("project/project.html", project=project_info, uploaded_data=uploaded_data)


########## HELPER CLASSES AND FUNCTIONS ##########

class folder(object):
    """ A class to parse the file list and do appropriate ops """
    def __init__(self, file_list):
        self.files = file_list
        self.files_arranged = {}
    
    def arrange_files(self):
        """ Method to arrange files that reflects folder structure """
        for _file in self.files:
            self.__parse_and_put_file(_file.name, _file.size, self.files_arranged)
    
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
            self.__parse_and_put_file(remaining_file_path, file_size, target_dict[parent_dir])
        else:
            target_dict[file_name] = file_size
    
    def __make_html_string_from_file_dict(self, file_dict):
        """ Takes a dict with files and creates html string with <ol> tag """
        _html_string = ""
        for _key, _value in file_dict.items():
            if isinstance(_value, dict):
                _html_string += "<li> {_k} {_v} </li>".format(_k=_key, _v=self.__make_html_string_from_file_dict(_value))
            else:
                _html_string += "<li> {_k} </li>".format(_k=_key)
        return '<ol class="nonumber"> {} </ol>'.format(_html_string)

