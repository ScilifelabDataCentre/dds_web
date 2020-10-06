from flask import Blueprint, g, jsonify, request
from flask_restful import Resource, Api
import json
from code_dds.models import Project, File
from code_dds.marshmallows import project_schema, projects_schema
from code_dds import db, app


def update_project_size(proj_id, altered_size, method, old_size: int = 0):
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
        elif method == 'update':
            # Existing file --> update project with file size
            current_project.size += (altered_size - old_size)
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
    def get(self, project):
        key = Project.query.filter_by(id=project).first()

        if key is None:
            return jsonify(message="There is no such project", project=project,
                           encrypted_key="", salt="",
                           nonce="")

        return jsonify(message="", project=project,
                       encrypted_key=key.private_key, salt=key.salt,
                       nonce=key.nonce)


class ProjectFiles(Resource):
    def get(self, project):
        '''Get all files for a specific project

        Args:
            project:    Project ID

        Returns:
            List of files in db
        '''

        # print("projects endpoint", flush=True)

        # Get all files belonging to project
        file_info = File.query.filter_by(project_id=project).all()

        # Return empty list if no files have been delivered
        if file_info is None:
            # print("HERE", flush=True)
            return jsonify(message="There are no files in project",
                           files=[])

        files = {}
        for file in file_info:
            files[file.name] = {'id': file.id,
                                'directory_path': file.directory_path,
                                'size': file.size,
                                'compressed': file.compressed,
                                'public_key': file.public_key,
                                'salt': file.salt}

        return jsonify(message="", files=files)


class DatabaseUpdate(Resource):
    def post(self):
        '''Add to or update file in database'''

        # Get all params from request
        all_ = request.args

        print("\nUpdating db...\n", flush=True)
        print(f"Type: {type(all_['size'])}")

        # Add file info to db
        try:
            # Get existing file
            existing_file = File.query.filter_by(
                name=all_['file'], project_id=all_['project']
            ).first()
        except Exception as e:
            print("\nError occurred! {e}\n", flush=True)
            return jsonify(updated=False, message=e)
        else:
            print("\nQuery successful!\n", flush=True)

            # Add new file if it doesn't already exist in db
            if existing_file is None:
                print("\nFile doesn't exist. Adding to db...\n", flush=True)

                try:
                    new_file = File(
                        name=all_['file'],
                        directory_path=all_['directory_path'],
                        size=int(all_['size']),
                        format="",
                        compressed=True if all_['ds_compressed'] else False,
                        public_key=all_['key'],
                        salt=all_['salt'],
                        project_id=int(all_['project'])
                    )
                except Exception as e:
                    return jsonify(updated=False, message=e)
                else:
                    print("\nAdding successful! Updating project size...\n", flush=True)

                    # Add new info to db
                    db.session.add(new_file)

                    # Update project size
                    proj_updated, error = update_project_size(
                        proj_id=all_['project'],
                        altered_size=int(all_['size']),
                        method="insert"
                    )

                    # If project size updated, commit to session to save to db
                    if proj_updated:
                        try:
                            db.session.commit()
                        except Exception as e:
                            return jsonify(updated=False, message=e)
                        else:
                            return jsonify(updated=True, message="")
                    else:
                        return jsonify(updated=False, message=error)
            else:
                if all_['overwrite']:
                    old_size = existing_file.size
                    # Update file if it exists in db
                    try:
                        existing_file.update(
                            dict(name=all_['file'],
                                 directory_path=all_['directory_path'],
                                 size=int(all_['size']),
                                 format="",
                                 compressed=True if all_[
                                'ds_compressed'] else False,
                                public_key=all_['key'],
                                salt=all_['salt'],
                                project_id=int(all_['project']))
                        )
                    except Exception as e:
                        return jsonify(updated=False, message=e)
                    else:
                        # Update project size
                        proj_updated, error = update_project_size(
                            proj_id=all_['project'],
                            altered_size=all_['size'],
                            method='update',
                            old_size=old_size
                        )

                        # If project size updated, commit to session to save to db
                        if proj_updated:
                            try:
                                db.session.commit()
                            except Exception as e:
                                return jsonify(updated=False, message=e)
                            else:
                                return jsonify(updated=True, message="")
                        else:
                            return jsonify(updated=False, message=error)
                else:
                    return jsonify(updated=False,
                                   message=("Trying to overwrite delivered "
                                            "file but 'overwrite' option not "
                                            "specified."))

        return jsonify(updated=True, message="")
