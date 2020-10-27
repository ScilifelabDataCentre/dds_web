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


class DatabaseUpdate(Resource):
    def post(self):
        '''Add to or update file in database.

        Returns:
            json: 
        '''

        # Get all params from request
        all_ = request.args

        # Validate token and cancel delivery if not valid
        ok = validate_token(all_["token"], all_["project"])
        if not ok:
            return jsonify(access_granted=False,
                           updated=False,
                           message="Token expired. Access denied.")

        # Add file info to db
        try:
            # Get existing file
            existing_file = File.query.filter_by(
                name=all_['file'], project_id=all_['project']
            ).first()
        except Exception as e:
            print("\nError occurred! {e}\n", flush=True)
            return jsonify(access_granted=True, updated=False, message=str(e))
        else:
            size = int(all_['size'])            # File size
            size_enc = int(all_['size_enc'])    # Encrypted file size

            # Add new file if it doesn't already exist in db
            if existing_file is None:
                try:
                    new_file = File(
                        name=all_['file'],
                        directory_path=all_['directory_path'],
                        size=size,
                        size_enc=size_enc,
                        extension=all_['extension'],
                        compressed=bool(all_['ds_compressed'] == "True"),
                        public_key=all_['key'],
                        salt=all_['salt'],
                        project_id=int(all_['project'])
                    )
                except Exception as e:
                    return jsonify(access_granted=True, updated=False,
                                   message=str(e))
                else:
                    # Add new info to db
                    db.session.add(new_file)

                    # Update project size
                    proj_updated, error = update_project_size(
                        proj_id=all_['project'],
                        altered_size=size,
                        altered_enc_size=size_enc,
                        method="insert"
                    )

                    # If project size updated, commit to session to save to db
                    if proj_updated:
                        try:
                            db.session.commit()
                        except Exception as e:
                            return jsonify(access_granted=True, updated=False,
                                           message=str(e))
                        else:
                            return jsonify(access_granted=True, updated=True,
                                           message="")
                    else:
                        return jsonify(access_granted=True, updated=False,
                                       message=error)
            else:
                if all_['overwrite']:
                    old_size = existing_file.size   # Curr file size in db
                    old_enc_size = existing_file.size_enc   # Curr enc size db

                    # Update file if it exists in db
                    try:
                        existing_file.name = all_['file']
                        existing_file.directory_path = all_['directory_path']
                        existing_file.size = size
                        existing_file.size_enc = size_enc
                        existing_file.extension = all_['extension']
                        existing_file.compressed = bool(all_['ds_compressed'])
                        existing_file.date_uploaded = timestamp()
                        existing_file.public_key = all_['key']
                        existing_file.salt = all_['salt']
                        existing_file.project_id = int(all_['project'])
                    except Exception as e:
                        return jsonify(access_granted=True, updated=False,
                                       message=str(e))
                    else:
                        # Update project size
                        proj_updated, error = update_project_size(
                            proj_id=all_['project'],
                            altered_size=size,
                            altered_enc_size=size_enc,
                            method='update',
                            old_size=old_size,
                            old_enc_size=old_enc_size
                        )

                        # If project size updated, commit to session to save to db
                        if proj_updated:
                            try:
                                db.session.commit()
                            except Exception as e:
                                return jsonify(access_granted=True,
                                               updated=False, message=str(e))
                            else:
                                return jsonify(access_granted=True,
                                               updated=True, message="")
                        else:
                            return jsonify(access_granted=True, updated=False,
                                           message=error)
                else:
                    return jsonify(access_granted=True, updated=False,
                                   message=("Trying to overwrite delivered "
                                            "file but 'overwrite' option not "
                                            "specified."))

        return jsonify(access_granted=True, updated=True, message="")
