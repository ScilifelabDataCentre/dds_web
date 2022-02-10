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


def __setup_unit():
    unit = models.Unit.query.filter_by(name="Unit 1").first()

    projects = unit.projects
    assert projects != []

    # Need empty projects to test the correct constraint
    for project in projects:
        __delete_files_and_versions(project)

    unit_users = unit.users
    assert unit_users != []

    return unit, projects, unit_users


def __delete_files_and_versions(project):
    for version in project.file_versions:
        db.session.delete(version)

    for file in project.files:
        db.session.delete(file)

    db.session.commit()


def test_delete_unit_row__with_project_and_users(client):
    """
    Unit row deleted when project and users are not deleted.

    Error
        Need to delete Project and UnitUser (due to inheritance issues) rows first
    """
    unit, _, _ = __setup_unit()

    db.session.delete(unit)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.commit()


def test_delete_unit_row__with_users(client):
    """
    Unit row deleted when users are not deleted.

    Error
        Need to delete UnitUsers (due to inheritance issues) rows first
    """
    unit, projects, _ = __setup_unit()

    for project in projects:
        db.session.delete(project)

    db.session.delete(unit)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.commit()


def test_delete_unit_row(client):
    """
    Unit row deleted when projects and users are deleted.

    Invite rows should be deleted
    """

    unit, projects, unit_users = __setup_unit()

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
def __setup_project():
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

    Error
        Need to delete File rows and Version rows first
    """
    project = __setup_project()

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.delete(project)
        db.session.commit()


def test_delete_project_with_files(client):
    """
    Project row deleted

    Error
        Need to delete File rows and Version rows first
    """
    project = __setup_project()

    for version in project.file_versions:
        db.session.delete(version)
    db.session.commit()

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.delete(project)
        db.session.commit()


def test_delete_project_with_versions(client):
    """
    Project row deleted

    Error
        Need to delete File rows and Version rows first
    """
    project = __setup_project()

    for file in project.files:
        db.session.delete(file)
    db.session.commit()

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.delete(project)
        db.session.commit()


def test_delete_project(client):
    """

    Project row deleted

    Unit row kept
    User row kept
    ProjectStatus rows deleted
    ProjectUser rows deleted
    """
    project = __setup_project()

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


# User ########################################################################################## User #


def __setup_user(username):
    user = models.User.query.filter_by(username=username).first()

    assert user.identifiers != []
    assert user.emails != []
    assert user.projects != []
    assert user.deletion_request is not None

    return user


def test_delete_user__researcher(client):
    """
    User row deleted

        Identifier rows deleted
        Email rows deleted
        Project rows kept
        DeletionRequest deleted
    """
    username = "researchuser"
    email_str = "researchuser@mailtrap.io"
    user = __setup_user(username)

    project_ids = [project.id for project in user.projects]
    nr_projects = len(project_ids)

    db.session.delete(user)
    db.session.commit()

    exists = models.User.query.filter_by(username=username).one_or_none()
    assert exists is None

    exists = models.ResearchUser.query.filter_by(username=username).one_or_none()
    assert exists is None

    # Make sure identifiers are deleted
    exists = models.Identifier.query.filter_by(username=username).one_or_none()
    assert exists is None

    # Make sure emails are deleted
    exists = models.Email.query.filter_by(email=email_str).one_or_none()
    assert exists is None

    # Make sure projects are kept
    project_ids_after = models.Project.query.filter(models.Project.id.in_(project_ids)).all()
    assert len(project_ids_after) == nr_projects

    # Make sure deletion request is deleted
    exists = models.DeletionRequest.query.filter_by(requester_id=username).one_or_none()
    assert exists is None


def test_delete_user__unituser(client):
    """
    User row deleted

        Identifier rows deleted
        Email rows deleted
        Project rows kept
        DeletionRequest deleted
    """
    username = "unituser"
    email_str = "unituser1@mailtrap.io"
    user = __setup_user(username)

    project_ids = [project.id for project in user.projects]
    nr_projects = len(project_ids)

    db.session.delete(user)
    db.session.commit()

    exists = models.User.query.filter_by(username=username).one_or_none()
    assert exists is None

    exists = models.UnitUser.query.filter_by(username=username).one_or_none()
    assert exists is None

    # Make sure identifiers are deleted
    exists = models.Identifier.query.filter_by(username=username).one_or_none()
    assert exists is None

    # Make sure emails are deleted
    exists = models.Email.query.filter_by(email=email_str).one_or_none()
    assert exists is None

    # Make sure projects are kept
    project_ids_after = models.Project.query.filter(models.Project.id.in_(project_ids)).all()
    assert len(project_ids_after) == nr_projects

    # Make sure deletion request is deleted
    exists = models.DeletionRequest.query.filter_by(requester_id=username).one_or_none()
    assert exists is None


def test_delete_user__superadmin(client):
    """
    User row deleted

        Identifier rows deleted
        Email rows deleted
        Project rows kept
        DeletionRequest deleted
    """
    username = "superadmin"
    email_str = "superadmin@mailtrap.io"
    user = __setup_user(username)

    project_ids = [project.id for project in user.projects]
    nr_projects = len(project_ids)

    db.session.delete(user)
    db.session.commit()

    exists = models.User.query.filter_by(username=username).one_or_none()
    assert exists is None

    exists = models.SuperAdmin.query.filter_by(username=username).one_or_none()
    assert exists is None

    # Make sure identifiers are deleted
    exists = models.Identifier.query.filter_by(username=username).one_or_none()
    assert exists is None

    # Make sure emails are deleted
    exists = models.Email.query.filter_by(email=email_str).one_or_none()
    assert exists is None

    # Make sure projects are kept
    project_ids_after = models.Project.query.filter(models.Project.id.in_(project_ids)).all()
    assert len(project_ids_after) == nr_projects

    # Make sure deletion request is deleted
    exists = models.DeletionRequest.query.filter_by(requester_id=username).one_or_none()
    assert exists is None


# Identifier ########################################################################## Identifier #


def __setup_identifier(username):
    identifier = models.Identifier.query.filter_by(username=username).first()

    assert identifier.user is not None
    return identifier


def test_delete_identifier(client):
    """
    Identifier row deleted

        User row kept
    """
    username = "researchuser"
    identifier = __setup_identifier(username)

    db.session.delete(identifier)
    db.session.commit()

    exists = models.Identifier.query.filter_by(username=username).one_or_none()
    assert exists is None

    exists = models.User.query.filter_by(username=username).one_or_none()
    assert exists is not None


# Email #################################################################################### Email #


def __setup_email(username):
    email = models.Email.query.filter_by(user_id=username).first()

    assert email.user is not None
    return email


def test_delete_email(client):
    """
    Email row deleted

        User row kept
    """
    username = "researchuser"
    email = __setup_email(username)

    db.session.delete(email)
    db.session.commit()

    exists = models.Email.query.filter_by(user_id=username).one_or_none()
    assert exists is None

    exists = models.User.query.filter_by(username=username).one_or_none()
    assert exists is not None


# Invite ################################################################################## Invite #


def __setup_invite(unit_name, invite_email):
    unit = models.Unit.query.filter_by(name=unit_name).first()
    invite = models.Invite(email=invite_email, role="Researcher")

    unit.invites.append(invite)

    db.session.add(invite)
    db.session.commit()

    invite = models.Invite.query.filter_by(email=invite_email).first()
    assert invite is not None
    assert invite.unit is not None

    return invite


def test_delete_invite(client):
    """
    Invite row deleted

        Unit row kept
    """
    unit_name = "Unit 1"
    invite_email = "invite_email@example.com"
    invite = __setup_invite(unit_name, invite_email)

    db.session.delete(invite)
    db.session.commit()

    exists = models.Invite.query.filter_by(email=invite_email).first()
    assert exists is None

    exists = models.Unit.query.filter_by(name=unit_name).first()
    assert exists is not None


# DeletionRequest ################################################################ DeletionRequest #


def __setup_deletion_request(username):
    deletion_request = models.DeletionRequest.query.filter_by(requester_id=username).first()
    assert deletion_request is not None
    assert deletion_request.requester is not None
    return deletion_request


def test_delete_deletion_request(client):
    """
    DeletionRequest row deleted

        User row kept
    """
    username = "researchuser"
    deletion_request = __setup_deletion_request(username)

    db.session.delete(deletion_request)
    db.session.commit()

    exists = models.DeletionRequest.query.filter_by(requester_id=username).one_or_none()
    assert exists is None

    exists = models.User.query.filter_by(username=username).one_or_none()
    assert exists is not None


# File ###################################################################################### File #


def __setup_file(filename):
    file = models.File.query.filter_by(name=filename).first()

    assert file is not None
    assert file.project is not None
    assert file.versions != []
    return file


def test_delete_file(client):
    """
    File row deleted

        Project row kept
        File versions kept
    """
    filename = "filename1"
    file = __setup_file(filename)

    project_id = file.project.id
    version_ids = [version.id for version in file.versions]

    db.session.delete(file)
    db.session.commit()

    exists = models.File.query.filter_by(name=filename).one_or_none()
    assert exists is None

    exists = models.Project.query.filter_by(id=project_id).one_or_none()
    assert exists is not None

    for version_id in version_ids:
        exists = models.Version.query.get(version_id)
        assert exists is not None


# Version ################################################################################ Version #


def __setup_version(file_id):
    versions = models.Version.query.filter_by(active_file=file_id).all()

    assert len(versions) == 1
    version = versions[0]
    assert version is not None
    assert version.file is not None
    assert version.project is not None
    return version


def test_delete_version(client):
    """
    Version row deleted

        File row kept
        Project row kept
    """
    filename = "filename2"
    file = models.File.query.filter_by(name=filename).first()
    file_id = file.id
    version = __setup_version(file_id)

    project_id = version.project.id

    db.session.delete(version)
    db.session.commit()

    exists = models.Version.query.filter_by(active_file=file_id).first()
    assert exists is None

    exists = models.File.query.filter_by(id=file_id).one_or_none()
    assert exists is not None

    exists = models.Project.query.filter_by(id=project_id).one_or_none()
    assert exists is not None
