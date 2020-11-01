from flask import Blueprint, g, jsonify, request
from flask_restful import Resource, Api
import json
from code_dds.models import Project, File, Tokens
from code_dds.marshmallows import project_schema, projects_schema
from code_dds import db, app, timestamp
from code_dds.api.login import validate_token


def update_project_size(proj_id, altered_size, altered_enc_size,
                        method, old_size: int = 0, old_enc_size: int = 0):
    '''Updates the specified project size'''

    try:
        # Get the current project in db
        current_project = Project.query.filter_by(id=proj_id).first()
    except Exception as e:
        return False, str(e)
    else:
        # Get the current project size
        # curr_size = current_project.size
        if method == 'insert':
            # New file --> add file size to project size
            current_project.size += altered_size
            current_project.size_enc += altered_enc_size
        elif method == 'update':
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
        except Exception as e:
            return False, str(e)
        else:
            # Project update successful
            return True, ""


class ListProjects(Resource):
    def get(self):
        all_projects = Project.query.all()
        return projects_schema.dump(all_projects)


class ProjectKey(Resource):
    def get(self, project, token):
        """Get project private key from database.

        Args:
            project:    Project ID
            token:      Token string in request

        Returns:
            json:   Error message, project ID, key, salt and nonce
        """

        # Validate token
        ok = validate_token(token, project)
        if not ok:
            return jsonify(access_granted=False,
                           message="Token expired. Access denied.",
                           project=project, encrypted_key="", salt="",
                           nonce="")

        try:
            key = Project.query.filter_by(id=project).first()
        except Exception as e:
            print(str(e), flush=True)
            return jsonify(access_granted=False,
                           message="Could not perform database query",
                           project=project, encrypted_key="", salt="",
                           nonce="")

        if key is None:
            return jsonify(access_granted=False,
                           message="There is no such project",
                           project=project, encrypted_key="", salt="",
                           nonce="")

        # TODO (ina): On project creation - encrypt passphrase with server-
        # known key and store in secure place. When download starts - get and
        # decrypt key, and then take the current user password (or token? or
        # both?) do encrypt the private key, which in the cli is decrypted and 
        # then can be used. 

        return jsonify(access_granted=True,
                       message="", project=project,
                       encrypted_key=key.private_key, salt=key.salt,
                       nonce=key.nonce)


class ProjectFiles(Resource):
    def get(self, project, token):
        '''Get all files for a specific project.

        Args:
            project:    Project ID

        Returns:
            List of files in db
        '''

        # Check if token is valid and cancel delivery if not
        ok = validate_token(token=token, project_id=project)
        if not ok:
            return jsonify(access_granted=False,
                           message="Token expired. Access denied.",
                           files=[])

        # Get all files belonging to project
        file_info = File.query.filter_by(project_id=project).all()

        # Return empty list if no files have been delivered
        if file_info is None:
            # print("HERE", flush=True)
            return jsonify(access_granted=False,
                           message="There are no files in project",
                           files=[])

        files = {}
        for file in file_info:
            files[file.name] = {'id': file.id,
                                'directory_path': file.directory_path,
                                'size': file.size,
                                'size_enc': file.size_enc,
                                'compressed': file.compressed,
                                'extension': file.extension,
                                'public_key': file.public_key,
                                'salt': file.salt}

        return jsonify(access_granted=True, message="", files=files)