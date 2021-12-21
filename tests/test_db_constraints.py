# IMPORTS ################################################################################ IMPORTS #

# Standard library

# Installed
from typing import no_type_check
import pytest
import sqlalchemy

# Own
import tests
import dds_web
from dds_web import db
from dds_web.database import models

# TESTS #################################################################################### TESTS #


# Unit ###################################################################################### Unit #


def __setup_unit(client):
    unit = models.Unit.query.filter_by(name="Unit 1").first()

    projects = unit.projects
    assert projects != []

    unit_users = unit.users
    assert unit_users != []

    return unit, projects, unit_users


def test_delete_unit_row__with_project_and_users(client):
    """
    Unit row deleted when project and users are not deleted.

    Error
        Need to delete Project and UnitUser (due to inheritance issues) rows first
        Invite rows deleted
    """
    unit, _, _ = __setup_unit(client)

    db.session.delete(unit)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.commit()


def test_delete_unit_row__with_users(client):
    """
    Unit row deleted when users are not deleted.

    Error
        Need to delete UnitUsers (due to inheritance issues) rows first
    """
    unit, projects, _ = __setup_unit(client)

    for project in projects:
        db.session.delete(project)
    db.session.commit()

    # Removing this print statement causes the test to fail on Johannes computer. I don't know why.
    print(unit.users)

    db.session.delete(unit)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.commit()


def test_delete_unit_row(client):
    """
    Unit row deleted when projects and users are deleted.

    Invite rows should be deleted
    """

    unit, projects, unit_users = __setup_unit(client)

    unit_id = unit.id
    # Make sure unit has some invites
    invites = unit.invites
    assert invites != []

    for project in projects:
        db.session.delete(project)

    for user in unit_users:
        db.session.delete(user)
    db.session.commit()

    db.session.delete(unit)
    db.session.commit()

    unit = models.Unit.query.filter_by(name="Unit 1").one_or_none()
    assert unit is None

    # Make sure invites have been deleted
    invites = models.Invite.query.filter_by(unit_id=unit_id).all()
    assert invites == []


# Project #################################################################################### Project #
def __setup_project(client):
    """
    Project with files and versions
    """
    project = models.Project.query.filter_by(public_id="public_project_id").first()

    # Make sure the project is well connected:
    assert project.files != []
    assert project.file_versions != []
    assert project.responsible_unit is not None
    assert project.responsible_unit.users != []
    assert project.researchusers != []

    statuses = models.ProjectStatuses.query.filter_by(project_id=project.id).all()
    assert statuses != []
    project_users = models.ProjectUsers.query.filter_by(project_id=project.id).all()
    assert project_users != []

    return project


def test_delete_project_with_files_and_versions(client):
    """
    Project row deleted

    Unit row kept
    User row kept
    Error
        Need to delete File rows and Version rows first
    ProjectStatus rows deleted
    ProjectUser rows deleted
    """
    project = __setup_project(client)

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.delete(project)
        db.session.commit()


def test_delete_project_with_files(client):
    """ """
    project = __setup_project(client)

    for version in project.file_versions:
        db.session.delete(version)
    db.session.commit()

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.delete(project)
        db.session.commit()


def test_delete_project(client):
    """ """
    project = __setup_project(client)

    project_id = project.id
    nr_users = models.User.query.count()
    nr_units = models.Unit.query.count()

    for version in project.file_versions:
        db.session.delete(version)
    db.session.commit()

    for file in project.files:
        db.session.delete(file)
    db.session.commit()

    db.session.delete(project)
    db.session.commit()

    exists = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    assert exists is None

    # Make sure no users or units have been deleted
    assert nr_users == models.User.query.count()
    assert nr_units == models.Unit.query.count()

    statuses = models.ProjectStatuses.query.filter_by(project_id=project_id).all()
    assert statuses == []
    project_users = models.ProjectUsers.query.filter_by(project_id=project_id).all()
    assert project_users == []
