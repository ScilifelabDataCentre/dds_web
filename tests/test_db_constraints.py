# IMPORTS ################################################################################ IMPORTS #

# Standard library

# Installed
import pytest
import sqlalchemy

# Own
import tests
import dds_web
from dds_web import db
from dds_web.database import models

# TESTS #################################################################################### TESTS #


# Unit ###################################################################################### Unit #


def test_delete_unit_row__with_project_and_users(client):
    """
    Unit row deleted when project and users are not deleted.

    Error
        Need to delete Project and UnitUser (due to inheritance issues) rows first
        Invite rows deleted
    """

    unit = models.Unit.query.filter_by(name="Unit 1").first()

    projects = unit.projects
    assert projects != []
    unit_users = unit.users
    assert unit_users != []

    db.session.delete(unit)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.commit()


def test_delete_unit_row__with_users(client):
    """
    Unit row deleted when users are not deleted.

    Error
        Need to delete UnitUsers (due to inheritance issues) rows first
    """

    unit = models.Unit.query.filter_by(name="Unit 1").first()

    projects = unit.projects
    assert projects != []
    unit_users = unit.users
    assert unit_users != []

    for project in projects:
        db.session.delete(project)
    db.session.commit()

    # With this removed, the exception does not occur
    # print(unit.users)

    db.session.delete(unit)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.commit()


def test_delete_unit_row__with_users2(client):
    """
    Unit row deleted when users are not deleted.

    Error
        Need to delete UnitUsers (due to inheritance issues) rows first
    """

    unit = models.Unit.query.filter_by(name="Unit 1").first()

    projects = unit.projects
    assert projects != []
    unit_users = unit.users
    assert unit_users != []

    for project in projects:
        db.session.delete(project)
    db.session.commit()

    # This seems to make the exception raise as it should below
    print(unit.users)

    db.session.delete(unit)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.commit()
