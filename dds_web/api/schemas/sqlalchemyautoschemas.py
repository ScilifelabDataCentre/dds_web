from dds_web import ma
from dds_web.database import models


class FileSchema(ma.SQLAlchemyAutoSchema):
    """ """

    class Meta:
        model = models.File
