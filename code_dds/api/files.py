from flask import jsonify
from flask_restful import Resource
from code_dds.models import File
from code_dds.marshmallows import file_schema, files_schema


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
