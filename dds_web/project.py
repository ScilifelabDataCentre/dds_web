" Project info related endpoints "

import os
import shlex
import shutil
import subprocess
import zipfile

from flask import (
    Blueprint,
    render_template,
    request,
    current_app,
    abort,
    session,
    url_for,
    g,
    jsonify,
    make_response,
    send_file,
    after_this_request,
)

from dds_web import db, timestamp
from dds_web.database import models
from dds_web.database import db_utils
from dds_web.crypt.key_gen import project_keygen
from dds_web.utils import login_required, working_directory, format_byte_size

project_blueprint = Blueprint("project", __name__)


@project_blueprint.route("/add_project", methods=["GET", "POST"])
@login_required
def add_project():
    """Add new project to the database"""
    if request.method == "POST":
        # Check no empty field from form
        for k in ["title", "owner", "description"]:
            if not request.form.get(k):
                return make_response(
                    jsonify({"status": 440, "message": f"Field '{k}' should not be empty"}), 440
                )

        ruser_obj = models.User.query.filter_by(username=request.form.get("owner")).one_or_none()
        cuser_obj = models.User.query.filter_by(username=session.get("current_user")).one()
        facility_obj = models.Facility.query.filter_by(id=session.get("facility_id")).one()
        # Check if the user actually exists
        if not ruser_obj or ruser_obj.role != "researcher":
            e_msg = "Given username '{}' does not exist".format(request.form.get("owner"))
            return make_response(jsonify({"status": 440, "message": e_msg}), 440)

        project_inst = create_project_instance(request.form)
        # TO DO : This part should be moved elsewhere to dedicated DB handling script
        new_project = models.Project(**project_inst.project_info)
        ruser_obj.projects.append(new_project)
        cuser_obj.projects.append(new_project)
        facility_obj.projects.append(new_project)
        db.session.add_all([new_project, ruser_obj, cuser_obj, facility_obj])
        db.session.commit()
        return make_response(
            jsonify(
                {
                    "status": 200,
                    "message": "Added new project '{}'".format(request.form.get("title")),
                    "project_id": new_project.public_id,
                }
            ),
            200,
        )


@project_blueprint.route("/<project_id>", methods=["GET"])
@login_required
def project_info(project_id=None):
    """Get the given project's info"""
    project_row = models.Project.query.filter_by(public_id=project_id).one_or_none()
    if not project_row:
        return abort(404, "Project doesn't exist")
    project_users = db_utils.get_project_users(project_id=project_row.id)
    if session.get("current_user") not in project_users:
        return abort(403, "You don't have access to this project")
    project_info = project_row.__dict__.copy()
    project_info["users"] = ", ".join(
        db_utils.get_project_users(project_id=project_row.id, no_facility_users=True)
    )
    project_info["date_created"] = timestamp(datetime_string=project_info["date_created"])
    if project_info.get("date_updated"):
        project_info["date_updated"] = timestamp(datetime_string=project_info["date_updated"])
    if project_info.get("size"):
        project_info["unformated_size"] = project_info["size"]
        project_info["size"] = format_byte_size(project_info["size"])
    project_info["facility_name"] = db_utils.get_facility_column(
        fid=project_info["facility_id"], column="name"
    )
    files_list = models.File.query.filter_by(project_id=project_info["id"]).all()
    if files_list:
        uploaded_data = dds_folder(files_list, project_id).generate_html_string()
    else:
        uploaded_data = None
    return render_template(
        "project/project.html",
        project=project_info,
        uploaded_data=uploaded_data,
        upload_limit=current_app.config.get("MAX_CONTENT_LENGTH"),
        download_limit=current_app.config.get("MAX_DOWNLOAD_LIMIT"),
        format_size=format_byte_size,
    )


@project_blueprint.route("upload", methods=["POST"])
@login_required
def data_upload():
    project_id = request.form.get("project_id", None)
    in_file_paths = request.form.getlist("file_paths")
    in_files = request.files.getlist("files")  # NB: request.files not request.form

    # Check that we got a project ID
    if project_id is None:
        return make_response(
            jsonify({"status": 433, "message": "Project ID not found in request"}), 433
        )

    # Check that something was uploaded
    if not in_files or len(in_files) == 0:
        return make_response(
            jsonify({"status": 433, "message": "No files were selected to upload"}), 433
        )

    # Check that we have the same number of files and paths
    if len(in_files) != len(in_file_paths):
        return make_response(
            jsonify(
                {
                    "status": 433,
                    "message": f"Number of uploaded files ({len(in_files)}) did not match number of file paths! ({len(in_file_paths)})",
                }
            ),
            433,
        )

    upload_space = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        "{}_T{}".format(project_id, timestamp(ts_format="%y%m%d%H%M%S")),
    )
    current_app.logger.info(f"Uploading {len(in_files)} files to {upload_space}")

    os.mkdir(upload_space)
    with working_directory(upload_space):
        upload_file_dest = os.path.abspath(os.path.join(upload_space, "data"))
        os.mkdir(upload_file_dest)
        for idx, in_file in enumerate(in_files):
            file_dir = os.path.join(upload_file_dest, os.path.dirname(in_file_paths[idx]))
            file_name = os.path.basename(in_file_paths[idx])
            if not os.path.isdir(file_dir):
                os.makedirs(file_dir)
            in_file.save(os.path.join(file_dir, file_name))

        with open("data_to_upload.txt", "w") as dfl:
            dfl.write(
                "\n".join([os.path.join(upload_file_dest, i) for i in os.listdir(upload_file_dest)])
            )

        cache_path = os.path.join(
            current_app.config.get("LOCAL_TEMP_CACHE"),
            "{}_{}_cache.json".format(session.get("current_user"), session.get("usid")),
        )
        proc = subprocess.Popen(
            shlex.split(
                f"dds put -c {cache_path} -p {project_id} -spf data_to_upload.txt --overwrite"
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = proc.communicate(input=None)

    resp = {"status": 200, "message": ""}
    if proc.returncode == 0:
        current_app.logger.info(out)
        resp = {"status": 200, "message": "Data successfully uploaded to S3"}

        # Get an updated file tree
        project_row = models.Project.query.filter_by(public_id=project_id).one_or_none()
        if project_row:
            project_info = project_row.__dict__.copy()
            files_list = models.File.query.filter_by(project_id=project_info["id"]).all()
            if files_list:
                resp["uploaded_data_html"] = dds_folder(
                    files_list, project_id
                ).generate_html_string()

        # Remove the temporary upload space
        try:
            shutil.rmtree(upload_space)
        except:
            print("Couldn't remove upload space '{}'".format(upload_space), flush=True)
            current_app.logger.error(err)
    else:
        resp = {"status": 515, "message": "Couldn't send data to S3"}
        current_app.logger.error(err)

    return make_response(jsonify(resp), resp["status"])


@project_blueprint.route("download/<project_id>", methods=["GET"])
@login_required
def data_download(project_id):
    data_path = request.form.get("data_path", None)
    download_space = os.path.join(
        current_app.config["DOWNLOAD_FOLDER"],
        "{}_T{}".format(project_id, timestamp(ts_format="%y%m%d%H%M%S")),
    )
    cache_path = os.path.join(
        current_app.config.get("LOCAL_TEMP_CACHE"),
        "{}_{}_cache.json".format(session.get("current_user"), session.get("usid")),
    )
    cmd = shlex.split(f"dds get -c {cache_path} -p {project_id} -d {download_space}")
    if data_path:
        cmd.extend(["-s", data_path])
    else:
        cmd.append("-a")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate(input=None)

    # Clean up after success
    @after_this_request
    def clean_download_space(response):
        if os.path.exists(download_space):
            try:
                shutil.rmtree(download_space)
            except Exception as e:
                current_app.logger.error(
                    "Couldn't delete download space {}".format(download_space), flush=True
                )
        return response

    if proc.returncode == 0:
        download_file_path = compile_download_file_path(download_space, project_id)
        return send_file(download_file_path, as_attachment=True)
    else:
        current_app.logger.error(err)
        abort(500, "Download failed, try again and if still see this message contact DC")


########## HELPER CLASSES AND FUNCTIONS ##########


class create_project_instance(object):
    """Creates a project instance to add in DB"""

    def __init__(self, project_info):
        self.project_info = {
            "public_id": self.get_new_id(),
            "title": project_info["title"],
            "description": project_info["description"],
            #            "owner": db_utils.get_user_column_by_username(project_info["owner"], "public_id"),
            "category": "testing",
            "facility_id": session.get("facility_id"),
            "status": "Ongoing",
            "date_created": timestamp(),
            "pi": "NA",
            "size": 0,
        }
        self.project_info["bucket"] = self.__create_bucket_name()
        pkg = project_keygen(self.project_info["public_id"])
        self.project_info.update(pkg.get_key_info_dict())

    def get_new_id(self, id=None):
        project_public_id = None
        while not project_public_id or not self.__is_column_value_uniq(
            "Project", "public_id", project_public_id
        ):
            facility_ref = db_utils.get_facility_column(
                fid=session.get("facility_id"), column="internal_ref"
            )
            facility_prjs = db_utils.get_facilty_projects(
                fid=session.get("facility_id"), only_id=True
            )
            project_public_id = "{}{:03d}".format(facility_ref, len(facility_prjs) + 1)
        return project_public_id

    def __is_column_value_uniq(self, table, column, value):
        """See that the value is unique in DB"""
        all_column_values = db_utils.get_full_column_from_table(table=table, column=column)
        return value not in all_column_values

    def __create_bucket_name(self):
        """Create a bucket name for the given project"""
        return "{pid}-{tstamp}-{rstring}".format(
            pid=self.project_info["public_id"].lower(),
            tstamp=timestamp(ts_format="%y%m%d%H%M%S%f"),
            rstring=os.urandom(4).hex(),
        )


class dds_folder(object):
    """A class to parse the file list and do appropriate ops"""

    def __init__(self, file_list, project_id):
        self.files = file_list
        self.project_id = project_id
        self.files_arranged = {}

    def arrange_files(self):
        """Method to arrange files that reflects folder structure"""
        for _file in self.files:
            self.__parse_and_put_file(_file.name, _file.size_original, self.files_arranged)

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
                _html_string += f"""
                    <li class="mb-1">
                        <a href="{url_for('project.data_download', project_id=self.project_id, data_path=_key) }" class="text-decoration-none">
                            <i class="far fa-arrow-to-bottom me-3 li-dwn-box"></i>
                        </a>
                        <a class="folder text-decoration-none" data-bs-toggle="collapse" href="#{div_id}" aria-expanded="false" aria-controls="{div_id}">
                            <i class="folder-icon far fa-folder me-2"></i>
                            {_key}
                        </a>
                        <div class="collapse" id="{div_id}"">
                            {self.__make_html_string_from_file_dict(_value)}
                        </div>
                    </li>"""
            else:
                _html_string += f"""
                    <li class="mb-1">
                        <a href="{url_for('project.data_download', project_id=self.project_id, data_path=_key) }" class="text-decoration-none">
                            <i class="far fa-arrow-to-bottom me-3 li-dwn-box"></i>
                        </a>
                        <code class="file">
                            {_key}
                        </code>
                        <span class="badge bg-light text-muted fw-light border font-monospace">
                            {format_byte_size(_value)}
                        </span>
                    </li>"""
        return f'<ul style="list-style: none;">{_html_string}</ul>'


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
