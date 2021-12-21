from dds_web import ma
from dds_web.database import models


class FileSchema(ma.SQLAlchemyAutoSchema):
    """Automatic schema for getting rows from the database."""

    class Meta:
        model = models.File
