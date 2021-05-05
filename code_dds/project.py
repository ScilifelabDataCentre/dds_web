" Project info related endpoints "

import os
import uuid
import subprocess
import shutil
import zipfile

from flask import (
    Blueprint,
    render_template,
    request,
    current_app,
    abort,
    session,
    redirect,
    url_for,
    g,
    jsonify,
    make_response,
    send_file,
    after_this_request,
)

from code_dds import db, timestamp
from code_dds.db_code import models
from code_dds.db_code import db_utils
from code_dds.db_code import marshmallows as marmal
from code_dds.crypt.key_gen import project_keygen
from code_dds.utils import login_required, working_directory, format_byte_size
from werkzeug.utils import secure_filename

project_blueprint = Blueprint("project", __name__)


@project_blueprint.route("/add_project", methods=["GET", "POST"])
@login_required
def add_project():
    """Add new project to the database"""
    if request.method == "GET":
        return render_template("project/add_project.html")
    if request.method == "POST":
        # Check no empty field from form
        for k in ["title", "owner", "description"]:
            if not request.form.get(k):
                return render_template(
                    "project/add_project.html",
                    error_message="Field '{}' should not be empty".format(k),
                )

        # Check if the user actually exists
        if request.form.get("owner") not in db_utils.get_full_column_from_table(
            table="User", column="username"
        ) or db_utils.get_user_column_by_username(request.form.get("owner"), "admin"):
            return render_template(
                "project/add_project.html",
                error_message="Given username '{}' does not exist".format(
                    request.form.get("owner")
                ),
            )

        project_inst = create_project_instance(request.form)
        # TO DO : This part should be moved elsewhere to dedicated DB handling script
        new_project = models.Project(**project_inst.project_info)
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for("project.project_info", project_id=new_project.id))


@project_blueprint.route("/<project_id>", methods=["GET"])
@login_required
def project_info(project_id=None):
    """Get the given project's info"""
    project_row = models.Project.query.filter_by(id=project_id).one_or_none()
    if not project_row:
        return abort(404)
    project_info = project_row.__dict__.copy()
    project_info["date_created"] = timestamp(datetime_string=project_info["date_created"])
    if project_info.get("date_updated"):
        project_info["date_updated"] = timestamp(datetime_string=project_info["date_updated"])
    if project_info.get("size"):
        project_info["unformated_size"] = project_info["size"]
        project_info["size"] = format_byte_size(project_info["size"])
    project_info["facility_name"] = db_utils.get_facility_column(
        fid=project_info["facility"], column="name"
    )
    files_list = models.File.query.filter_by(project_id=project_id).all()
    if files_list:
        uploaded_data = folder(files_list).generate_html_string()
    else:
        uploaded_data = None
    return render_template(
        "project/project.html",
        project=project_info,
        uploaded_data=uploaded_data,
        download_limit=current_app.config.get("MAX_DOWNLOAD_LIMIT"),
        format_size=format_byte_size,
    )


@project_blueprint.route("upload", methods=["POST"])
@login_required
def data_upload():
    project_id = request.form.get("project_id", None)
    in_files = validate_file_list(request.files.getlist("files")) or validate_file_list(
        request.files.getlist("folder")
    )
    upload_space = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        "{}_T{}".format(project_id, timestamp(ts_format="%y%m%d%H%M%S")),
    )
    if project_id is None:
        status, message = (433, "Project ID not found in request")
    elif not in_files:
        status, message = (434, "No files/folder were selected")
    else:
        os.mkdir(upload_space)
        with working_directory(upload_space):
            upload_file_dest = os.path.join(upload_space, "data")
            os.mkdir(upload_file_dest)
            for in_file in in_files:
                file_target_path = upload_file_dest
                path_splitted = in_file.filename.split("/")
                filename = path_splitted[-1]  # TO DO: look into secure naming
                if len(path_splitted) > 1:
                    for p in path_splitted[:-1]:
                        file_target_path = os.path.join(file_target_path, p)
                        if not os.path.exists(file_target_path):
                            os.mkdir(file_target_path)
                in_file.save(os.path.join(file_target_path, filename))

            with open("data_to_upload.txt", "w") as dfl:
                dfl.write(
                    "\n".join(
                        [os.path.join(upload_file_dest, i) for i in os.listdir(upload_file_dest)]
                    )
                )

            proc = subprocess.Popen(
                [
                    "dds",
                    "put",
                    "-c",
                    os.path.join(
                        current_app.config.get("LOCAL_TEMP_CACHE"),
                        "{}_{}_cache.json".format(session.get("current_user"), session.get("usid")),
                    ),
                    "-p",
                    project_id,
                    "-spf",
                    "data_to_upload.txt",
                    "--overwrite",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, err = proc.communicate(input=None)

        if proc.returncode == 0:
            status, message = (200, "Data successfully uploaded to S3")
            try:
                shutil.rmtree(upload_space)
            except:
                print("Couldn't remove upload space '{}'".format(upload_space), flush=True)
        else:
            status, message = (515, "Couldn't send data to S3")

    return make_response(jsonify({"status": status, "message": message}), status)


@project_blueprint.route("download", methods=["POST"])
@login_required
def data_download():
    project_id = request.form.get("project_id", None)
    data_path = request.form.get("data_path", None)
    download_space = os.path.join(
        current_app.config["DOWNLOAD_FOLDER"],
        "{}_T{}".format(project_id, timestamp(ts_format="%y%m%d%H%M%S")),
    )
    cmd = [
        "dds",
        "get",
        "-c",
        os.path.join(
            current_app.config.get("LOCAL_TEMP_CACHE"),
            "{}_{}_cache.json".format(session.get("current_user"), session.get("usid")),
        ),
        "-p",
        project_id,
        "-d",
        download_space,
    ]
    if data_path:
        cmd.append("-s")
        cmd.append(data_path)
    else:
        cmd.append("-a")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate(input=None)

    # cleanup after success
    @after_this_request
    def clean_download_space(response):
        if os.path.exists(download_space):
            try:
                shutil.rmtree(download_space)
            except Exception as e:
                print(
                    "Couldn't delete download space {}".format(download_space),
                    flush=True,
                )
        return response

    if proc.returncode == 0:
        download_file_path = compile_download_file_path(download_space, project_id)
        return send_file(download_file_path, as_attachment=True)
    else:
        abort(500, "Download failed, try again and if still see this message contact DC")


########## HELPER CLASSES AND FUNCTIONS ##########


class create_project_instance(object):
    """Creates a project instance to add in DB"""

    def __init__(self, project_info):
        self.project_info = {
            "id": self.get_new_id(),
            "title": project_info["title"],
            "description": project_info["description"],
            "owner": db_utils.get_user_column_by_username(project_info["owner"], "public_id"),
            "category": "testing",
            "facility": g.current_user_id,
            "status": "Ongoing",
            "date_created": timestamp(),
            "pi": "NA",
            "size": 0,
        }
        self.project_info["bucket"] = "{}_bucket".format(self.project_info["id"])
        pkg = project_keygen(self.project_info["id"])
        self.project_info.update(pkg.get_key_info_dict())

    def get_new_id(self, id=None):
        facility_ref = db_utils.get_facility_column(
            fid=session.get("current_user_id"), column="internal_ref"
        )
        facility_prjs = db_utils.get_facilty_projects(
            fid=session.get("current_user_id"), only_id=True
        )
        return "{}{:03d}".format(facility_ref, len(facility_prjs) + 1)

    def __is_column_value_uniq(self, table, column, value):
        """See that the value is unique in DB"""
        all_column_values = db_utils.get_full_column_from_table(table=table, column=column)
        return value not in all_column_values


class folder(object):
    """A class to parse the file list and do appropriate ops"""

    def __init__(self, file_list):
        self.files = file_list
        self.files_arranged = {}

    def arrange_files(self):
        """Method to arrange files that reflects folder structure"""
        for _file in self.files:
            self.__parse_and_put_file(_file.name, _file.size, self.files_arranged)

    def generate_html_string(self, arrange=True):
        """Generates html string for the files to pass in template"""
        if arrange and not self.files_arranged:
            self.arrange_files()

        return self.__make_html_string_from_file_dict(self.files_arranged)

    def __parse_and_put_file(self, file_name, file_size, target_dict):
        """Private method that actually"""
        file_name_splitted = file_name.split("/", 1)
        if len(file_name_splitted) == 2:
            parent_dir, remaining_file_path = file_name_splitted
            if parent_dir not in target_dict:
                target_dict[parent_dir] = {}
            self.__parse_and_put_file(remaining_file_path, file_size, target_dict[parent_dir])
        else:
            target_dict[file_name] = file_size

    def __make_html_string_from_file_dict(self, file_dict):
        """Takes a dict with files and creates html string with <ol> tag"""
        _html_string = ""
        for _key, _value in file_dict.items():
            if isinstance(_value, dict):
                div_id = "d{}".format(timestamp(ts_format="%y%m%d%H%M%S%f"))
                _html_string += (
                    "<li>"
                    " <span class='li-dwn-box'></span>"
                    " <a class='folder' data-toggle='collapse' href='#{did}' aria-expanded='false' aria-controls='{did}'>{_k}</a> "
                    " <div class='collapse' id='{did}'>{_v}</div> "
                    "</li>"
                ).format(
                    did=div_id,
                    _k=_key,
                    _v=self.__make_html_string_from_file_dict(_value),
                )
            else:
                _html_string += (
                    "<li>"
                    "  <span class='li-dwn-box'></span>"
                    "  <div class='hovertip'>"
                    "    <span class='file'>{_k}</span> <span class='hovertiptext hovertiptext-filesize'> {_v} </span>"
                    "  </div>"
                    "</li>"
                ).format(_k=_key, _v=format_byte_size(_value))
        return '<ul style="list-style: none;"> {} </ul>'.format(_html_string)


def compile_download_file_path(dpath, pid):
    with working_directory(dpath):
        pname = "{}_data".format(pid)
        os.rename("files", pname)
        contents = os.listdir(pname)
        if len(contents) == 1:
            cpath = os.path.join(pname, contents[0])
            if os.path.isfile(cpath):
                return os.path.join(dpath, cpath)
        zname = "{}.zip".format(pname)
        with zipfile.ZipFile(zname, "w") as pz:
            for pdir, sdir, files in os.walk(pname):
                for fl in files:
                    pz.write(os.path.join(pdir, fl))
        return os.path.join(dpath, zname)


def validate_file_list(flist):
    """Helper function to check if the file list from upload have files"""
    return False if (len(flist) == 1 and flist[0].filename == "") else flist
