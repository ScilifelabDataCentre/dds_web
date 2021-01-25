"""Project-related API endpoints and functions."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import json
import pathlib

# Installed
import flask
import flask_restful
import sqlalchemy

# Own modules
from code_dds import db
from code_dds.db_code import marshmallows as marmal
from code_dds.db_code import models
from code_dds.api import login


###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################

def get_passphrase(project_id):
    """Gets the passphrase used for encrypting the private key."""

    try:
        passphrase = models.Project.query.filter_by(
            id=project_id).with_entities(models.Project.passphrase).first()
    except sqlalchemy.exc.SQLAlchemyError as e:
        print(str(e), flush=True)
        return {"error": str(e), "PRIVKEY_ENC_PASSPHRASE": ""}

    if passphrase is None:
        return {"error": "There is no passphrase for the current project.",
                "PRIVKEY_ENC_PASSPHRASE": ""}

    return {"PRIVKEY_ENC_PASSPHRASE": passphrase[0], "error": ""}
    # TODO (ina): Change this!!!
    # passp_path = pathlib.Path.cwd() / \
    #     pathlib.Path(f"sensitive/passphrase_{project_id}.json")
    # try:
    #     with passp_path.open(mode="r") as f:
    #         passp_info = json.load(f)
    # except IOError as ioe:
    #     print(ioe, flush=True)

    # return passp_info


def update_project_size(proj_id, altered_size, altered_enc_size,
                        method, old_size: int = 0, old_enc_size: int = 0):
    """Updates the specified project size"""

    try:
        # Get the current project in db
        current_project = models.Project.query.filter_by(id=proj_id).first()
    except sqlalchemy.exc.SQLAlchemyError as e:
        return False, str(e)
    else:
        # Get the current project size
        # curr_size = current_project.size
        if method == "insert":
            # New file --> add file size to project size
            current_project.size += altered_size
            current_project.size_enc += altered_enc_size
        elif method == "update":
            # Existing file --> update project with file size
            current_project.size += (altered_size - old_size)
            current_project.size_enc += (altered_size - old_enc_size)
        else:
            # User tried an unspecified method
            return False, (f"Method {method} not applicable when "
                           "updating project size")

        # Commit db session to save to db
        try:
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as e:
            return False, str(e)
        else:
            # Project update successful
            return True, ""


###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################

class ListProjects(flask_restful.Resource):
    """Lists all projects in database."""

    def get(self):
        """Gets projects from database and returns request response."""

        all_projects = models.Project.query.all()
        return marmal.projects_schema.dump(all_projects)


class ProjectKey(flask_restful.Resource):
    """Endpoint for getting the project specific key."""

    def get(self, project):
        """Get project private key from database.

        Args:
            project:    Project ID
            token:      Token string in request

        Returns:
            json:   Error message, project ID, key, salt and nonce
        """

        token = flask.request.args["token"]
        # Validate token
        ok_ = login.validate_token(token, project)
        if not ok_:
            return flask.jsonify(access_granted=False,
                                 message="Token expired. Access denied.",
                                 project=project, encrypted_key="", salt="",
                                 nonce="", passphrase="")

        try:
            key = models.Project.query.filter_by(id=project).first()
        except sqlalchemy.exc.SQLAlchemyError as e:
            print(str(e), flush=True)
            return flask.jsonify(access_granted=False,
                                 message="Could not perform database query",
                                 project=project, encrypted_key="", salt="",
                                 nonce="", passphrase="")

        if key is None:
            return flask.jsonify(access_granted=False,
                                 message="There is no such project",
                                 project=project, encrypted_key="", salt="",
                                 nonce="", passphrase="")

        # TODO (ina): On project creation - encrypt passphrase with server-
        # known key and store in secure place. When download starts - get and
        # decrypt key, and then take the current user password (or token? or
        # both?) do encrypt the private key, which in the cli is decrypted and
        # then can be used.
        # TODO (ina): This should NOT be in the same request later.
        passp = get_passphrase(project)

        if passp["error"] != "":
            return flask.jsonify(access_granted=False,
                                 message=passp["error"],
                                 project=project, encrypted_key="", salt="",
                                 nonce="", passphrase="")

        return flask.jsonify(access_granted=True,
                             message="", project=project,
                             encrypted_key=key.private_key, salt=key.salt,
                             nonce=key.nonce,
                             passphrase=passp["PRIVKEY_ENC_PASSPHRASE"])


class ProjectFiles(flask_restful.Resource):
    """Endpoint for getting files connected to a specific project."""

    def get(self, proj_id):
        """Get all files for a specific project.

        Args:
            project:    Project ID

        Returns:
            List of files in db
        """

        token = flask.request.args["token"]

        # Check if token is valid and cancel delivery if not
        ok_ = login.validate_token(token=token,
                                   project_id=proj_id)
        if not ok_:
            return flask.jsonify(access_granted=False,
                                 message="Token expired. Access denied.",
                                 files=[])

        # Get all files belonging to project
        file_info = models.File.query.filter_by(project_id=proj_id).all()

        # Return empty list if no files have been delivered
        if file_info is None:
            return flask.jsonify(access_granted=True,
                                 message="There are no files in project",
                                 files=[])

        files = {}
        for file in file_info:
            files[file.name] = {"id": file.id,
                                "directory_path": file.directory_path,
                                "size": file.size,
                                "size_enc": file.size_enc,
                                "compressed": file.compressed,
                                "extension": file.extension,
                                "public_key": file.public_key,
                                "salt": file.salt}

        return flask.jsonify(access_granted=True, message="", files=files)

    def post(self, proj_id):
        """Docstring"""

        # Get token from request header
        token = flask.request.headers["token"]

        # Check if token is valid and cancel delivery if not
        ok_ = login.validate_token(token=token,
                                   project_id=proj_id)
        if not ok_:
            return flask.jsonify(access_granted=False,
                                 message="Token expired. Access denied.",
                                 files=[])

        # Get all files and iterate through the files from CLI
        # NOTE: Atm this is the fastest method. Test to iterate through files
        # and perform queries each time later when DB is full with files.
        # Faster? Doubt it but check.
        prevup_files = list()
        matching_files = dict()
        files = dict()

        # if flask.request.headers["method"] == "put":
        try:
            # Get all files from db which are in the files set from CLI
            # and belong to the current project
            prevup_files = models.File.query.filter(
                models.File.name.in_(flask.request.json)
            ).filter_by(project_id=proj_id).all()

            print(
                f"All files: {prevup_files}, type: {type(prevup_files)}", flush=True)
        except sqlalchemy.exc.SQLAlchemyError as e:
            # TODO (ina): Add real error message
            # return flask.jsonify(message="FAILED - ADD NEW MESSAGE HERE")
            print(str(e), flush=True)
        else:
            # Do additional checks if no matching files were found
            if not prevup_files or prevup_files is None:
                if flask.request.headers["method"] == "put":
                    return flask.jsonify(
                        access_granted=True,
                        message="Currently no files uploaded in project.",
                        files=[]
                    )
                
                # Get: Check if the path is a folder (directory_path
                # beginning with path)
                try:
                    prevup_files = models.File.query.filter(
                        models.File.directory_path.like(
                            [f"{x}%" for x in flask.request.json]
                        )
                    ).filter_by(project_id=proj_id).all()
                except sqlalchemy.exc.SQLAlchemyError as e:
                    print(str(e), flush=True)

            matching_files = {x.name: {"id": x.id,
                                  "directory_path": x.directory_path,
                                  "size": x.size,
                                  "size_enc": x.size_enc,
                                  "compressed": x.compressed,
                                  "extension": x.extension,
                                  "public_key": x.public_key,
                                  "salt": x.salt} for x in prevup_files}

        # Save and return the previously uploaded
        # for x in flask.request.json:
        #     # Remove filename from matching files and put into
        #     # new file dict if file from CLI request in the matching paths
        #     if x in matching_files:
        #         files[x] = matching_files.pop(x)

        # matching_files = None

        return flask.jsonify(access_granted=True, message="", files=matching_files)
