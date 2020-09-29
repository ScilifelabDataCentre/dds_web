from flask_restful import Resource
from code_dds.models import File
from code_dds.marshmallows import file_schema, files_schema


class ListFiles(Resource):
    def get(self):
        all_files = File.query.all()
        return files_schema.dump(all_files)
