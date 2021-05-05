""" Utility function that makes DB calls """

from code_dds import db
from code_dds.db_code import models


def get_facility_column(fid, column) -> (str):
    """Gets the columns value from DB for given facility ID"""
    facility = models.Facility.query.filter_by(public_id=fid).first()
    return getattr(facility, column)


def get_facility_column_by_username(fname, column) -> (str):
    """Gets the columns value from DB for given facility username"""
    facility = models.Facility.query.filter_by(username=fname).first()
    return getattr(facility, column)


def get_facilty_projects(fid, only_id=False) -> (list):
    """Gets all the project for the facility ID"""
    project_list = models.Project.query.filter_by(facility=fid).all()
    return project_list if not only_id else [prj.id for prj in project_list]


def get_user_column_by_username(username, column) -> (str):
    """Gets the columns value from DB for given username"""
    user = models.User.query.filter_by(username=username).first()
    return getattr(user, column)


def get_user_projects(uid, only_id=False) -> (list):
    """Gets all the project for the username ID"""
    project_list = models.Project.query.filter_by(owner=uid).all()
    return project_list if not only_id else [prj.id for prj in project_list]


def get_full_column_from_table(table, column) -> (list):
    """Get the whole column from the given table"""
    mtable = getattr(models, table)
    return [entry[0] for entry in mtable.query.with_entities(getattr(mtable, column)).all()]
