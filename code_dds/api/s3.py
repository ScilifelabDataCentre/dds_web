from flask_restful import Resource
from code_dds.models import S3Project
from code_dds.marshmallows import s3_schema, s3s_schema
import pathlib
import json


class ListS3(Resource):
    def get(self):
        all_s3projects = S3Project.query.all()
        return s3s_schema.dump(all_s3projects)


class S3Info(Resource):
    def get(self):
        s3path = pathlib.Path.cwd() / \
                pathlib.Path("sensitive/s3_config.json")
        with s3path.open(mode="r") as f:
            s3creds = json.load(f)

        return s3creds