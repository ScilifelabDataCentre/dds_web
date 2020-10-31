from flask import jsonify, request
from flask_restful import Resource
from code_dds.models import File
from code_dds.marshmallows import file_schema, files_schema
from sqlalchemy import func
from code_dds import db
from datetime import datetime as dt
from code_dds import timestamp
from code_dds.api.login import validate_token
from code_dds.api.project import update_project_size


class ListFiles(Resource):
    def get(self):
        all_files = File.query.all()
        return files_schema.dump(all_files)


class FileSalt(Resource):
    def get(self, file_id):
        file_salt = File.query.filter_by(id=file_id)

        if file_salt is None:
            return jsonify(found=False, salt="")

        return jsonify(found=True, salt=file_salt.salt)


class DeliveryDate(Resource):
    def post(self):
        """Update latest download date in file database.

        Returns:
            json:   If updated
        """

        # Validate token and cancel delivery if not valid
        token = request.args["token"]
        project = request.args["project"]
        ok = validate_token(token, project)
        if not ok:
            return jsonify(access_granted=False,
                           updated=False,
                           message="Token expired. Access denied.")

        # Get file id
        file_id = request.args['file_id']

        # Update file info
        try:
            file = File.query.filter_by(id=int(file_id)).first()
        except Exception as e:
            print(str(e), flush=True)
            return jsonify(access_granted=True, updated=False, message=str(e))

        if file is None:
            emess = "The file does not exist in the database, cannot update."
            print(emess, flush=True)
            return jsonify(access_granted=True, updated=False, message=emess)

        # Update download time
        try:
            file.latest_download = timestamp()
        except Exception as e:
            print(str(e), flush=True)
            return jsonify(access_granted=True, updated=False, message=str(e))
        else:
            db.session.commit()

        return jsonify(access_granted=True, updated=True, message="")


class FileUpdate(Resource):
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
