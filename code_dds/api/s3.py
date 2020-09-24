from flask_restful import Resource
from code_dds.models import S3Project
from code_dds.marshmallows import s3_schema, s3s_schema


class ListS3(Resource):
    def get(self):
        all_s3projects = S3Project.query.all()
        return s3s_schema.dump(all_s3projects)
