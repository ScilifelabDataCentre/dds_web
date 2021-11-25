from dds_web import ma
from dds_web.database import models
import marshmallow
from dds_web.api import api_s3_connector
from dds_web.api.schemas import project_schemas
import flask


class FileSchema(ma.Schema):
    class Meta:
        model = models.File

    @marshmallow.post_dump
    def get_stuff(self, data, many, **kwargs):
        flask.current_app.logger.debug(f"project: {data.get('project_row')}")
        if many and "name" in data:
            filename = data.pop("name")
            return {filename: data}

        return data
