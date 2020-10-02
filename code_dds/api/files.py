from flask import jsonify, request
from flask_restful import Resource
from code_dds.models import File
from code_dds.marshmallows import file_schema, files_schema
from sqlalchemy import func
from code_dds import db
from datetime import datetime as dt


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

        # print("TEST:", flush=True)
        file_id = request.args['file_id']
        # print(f"TEST: {file_id}", flush=True)
        # print(f"file id? {file_id['file_id']}", flush=True)
        # print(type(file_id), flush=True)
        file = File.query.filter_by(id=int(file_id)).first()
        # print(f"{file.id}", flush=True)
        file.latest_download = dt.now()
        # db.session.add(file)
        db.session.commit()

        return jsonify(true=True)
