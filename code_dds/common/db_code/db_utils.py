""" Utility function that makes DB calls """

from code_dds import db
from code_dds.common.db_code import models

def get_facility_column(fid, column) -> (str):
    """ Gets the columns value from DB for given facility ID """
    facility = models.Facility.query.filter_by(id=fid).first()
    return getattr(facility, column)

def get_full_column_from_table(table, column) -> (list):
    """ Get the whole column from the given table """
    mtable = getattr(models, table)
    return [entry[0] for entry in mtable.query.with_entities(getattr(mtable, column)).all()]
    