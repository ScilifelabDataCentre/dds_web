"""Project-related API endpoints and functions."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
import flask
import flask_restful
import sqlalchemy

# Own modules
from code_dds import db
from code_dds import marshmallows as marmal
from code_dds import models
from code_dds.api import login


###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################

def update_project_size(proj_id, altered_size, altered_enc_size,
                        method, old_size: int = 0):
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
            current_project.size_enc += (altered_size - old_size)
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

    def get(self, project, token):
        """Get project private key from database.

        Args:
            project:    Project ID
            token:      Token string in request

        Returns:
            json:   Error message, project ID, key, salt and nonce
        """

        # Validate token
        ok_ = login.validate_token(token, project)
        if not ok_:
            return flask.jsonify(access_granted=False,
                           message="Token expired. Access denied.",
                           project=project, encrypted_key="", salt="",
                           nonce="")

        try:
            key = models.Project.query.filter_by(id=project).first()
        except sqlalchemy.exc.SQLAlchemyError as e:
            print(str(e), flush=True)
            return flask.jsonify(access_granted=False,
                           message="Could not perform database query",
                           project=project, encrypted_key="", salt="",
                           nonce="")

        if key is None:
            return flask.jsonify(access_granted=False,
                           message="There is no such project",
                           project=project, encrypted_key="", salt="",
                           nonce="")

        # TODO (ina): On project creation - encrypt passphrase with server-
        # known key and store in secure place. When download starts - get and
        # decrypt key, and then take the current user password (or token? or
        # both?) do encrypt the private key, which in the cli is decrypted and
        # then can be used.

        return flask.jsonify(access_granted=True,
                       message="", project=project,
                       encrypted_key=key.private_key, salt=key.salt,
                       nonce=key.nonce)


class ProjectFiles(flask_restful.Resource):
    """Endpoint for getting files connected to a specific project."""

    def get(self, project, token):
        """Get all files for a specific project.

        Args:
            project:    Project ID

        Returns:
            List of files in db
        """

        # Check if token is valid and cancel delivery if not
        ok_ = login.validate_token(token=token, project_id=project)
        if not ok_:
            return flask.jsonify(access_granted=False,
                           message="Token expired. Access denied.",
                           files=[])

        # Get all files belonging to project
        file_info = models.File.query.filter_by(project_id=project).all()

        # Return empty list if no files have been delivered
        if file_info is None:
            # print("HERE", flush=True)
            return flask.jsonify(access_granted=False,
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
