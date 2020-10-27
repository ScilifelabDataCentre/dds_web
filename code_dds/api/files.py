from flask import jsonify, request
from flask_restful import Resource
from code_dds.models import File
from code_dds.marshmallows import file_schema, files_schema
from sqlalchemy import func
from code_dds import db
from datetime import datetime as dt
from code_dds import timestamp
from code_dds.api.login import validate_token


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
