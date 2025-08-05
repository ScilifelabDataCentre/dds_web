# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
from sqlite3 import OperationalError
import pytest
from _pytest.logging import LogCaptureFixture
import logging
import datetime
import time
import unittest.mock
from unittest.mock import MagicMock
from unittest.mock import patch

# Installed
import boto3
import flask_mail
import werkzeug
import sqlalchemy

# Own
import dds_web
from dds_web import mail, db
from dds_web.errors import BucketNotFoundError, DatabaseError, DeletionError
import tests
from tests.test_files_new import project_row, file_in_db, FIRST_NEW_FILE
from tests.test_project_creation import proj_data_with_existing_users, create_unit_admins
from dds_web.database import models
from dds_web.api.project import UserProjects

# CONFIG ################################################################################## CONFIG #

proj_data = {
    "pi": "researchuser@mailtrap.io",
    "title": "Test proj",
    "description": "A longer project description",
    "users_to_add": [{"email": "researchuser2@mailtrap.io", "role": "Project Owner"}],
}
fields_set_to_null = [
    "title",
    "date_created",
    "description",
    "pi",
    "public_key",
    # "unit_id",
    # "created_by",
    # "is_active",
    # "date_updated",
]

release_project = {"new_status": "Available"}
release_project_small_deadline = {**release_project, "deadline": 5}
release_project_big_deadline = {**release_project, "deadline": 80}

extend_deadline_data_no_confirmed = {
    "new_deadline_in": 20,
}

extend_deadline_data = {**extend_deadline_data_no_confirmed, "confirmed": True}


# HELPER FUNCTIONS ################################################################################## CONFIG #


def create_and_release_project(client, proj_data, release_data):
    """Helper function that creates a project and set it ups as available"""

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    # Release project
    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project_id},
        json=release_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    return project_id, project


@pytest.fixture(scope="module")
def test_project(module_client):
    """Create a shared test project"""
    with unittest.mock.patch.object(boto3.session.Session, "resource") as mock_session:
        response = module_client.post(
            tests.DDSEndpoint.PROJECT_CREATE,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
            json=proj_data,
        )
        project_id = response.json.get("project_id")
    # add a file
    response = module_client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=FIRST_NEW_FILE,
    )

    return project_id


def mock_sqlalchemyerror(_=None):
    raise sqlalchemy.exc.SQLAlchemyError()


def mock_typeerror(_=None):
    raise TypeError


def mock_databaseerror(_=None):
    raise DatabaseError


def mock_deletionerror(_=None):
    raise DeletionError()


def mock_bucketnotfounderror(_=None):
    raise BucketNotFoundError()


def mock_operationalerror(_=None):
    raise sqlalchemy.exc.OperationalError


def mock_attributeerror():
    raise AttributeError


# ProjectStatus

# get


def test_projectstatus_get_status_without_args(module_client, boto3_session):
    """Submit status request with invalid arguments"""
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    # Create project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    # Test getting project status without args - should fail
    response = module_client.get(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        json={},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Missing required information: 'project'" in response.json["message"]

    # Test getting project status without args version 2 - should fail
    response = module_client.get(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        json={},
        query_string={},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Missing required information: 'project'" in response.json["message"]


def test_projectstatus_get_status_with_empty_args(module_client, boto3_session):
    """Submit status request with invalid arguments"""
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    # Create project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    # Test getting project status without args - should fail
    response = module_client.get(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        json={},
        query_string={"test": "test"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Missing required information: 'project'" in response.json["message"]


def test_projectstatus_get_status_with_invalid_project(module_client, boto3_session):
    """Submit status request with invalid arguments"""
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    # Create project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    # Test getting project status without args - should fail
    response = module_client.get(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        json={},
        query_string={"project": "nonexistentproject"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "The specified project does not exist." in response.json["message"]


def test_projectstatus_get_status_with_non_accessible_project(module_client, boto3_session):
    """Submit status request with invalid arguments"""
    # Get project for unit 2
    project = models.Project.query.filter_by(unit_id=2).first()
    assert project

    # Test getting project status without args - should fail
    response = module_client.get(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        json={},
        query_string={"project": project.public_id},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "Project access denied." in response.json["message"]


# set_busy


def test_set_busy_true(module_client):
    """Test set busy to true."""
    from dds_web.api import project

    # Get project
    project_obj = models.Project.query.first()
    assert project_obj

    # Set as not busy
    project_obj.busy = False
    db.session.commit()

    # Run function
    project.ProjectStatus.set_busy(project=project_obj, busy=True)
    assert project_obj.busy


def test_set_busy_false(module_client):
    """Test set busy to false."""
    from dds_web.api import project

    # Get project
    project_obj = models.Project.query.first()
    assert project_obj

    # Set as not busy
    project_obj.busy = True
    db.session.commit()

    # Run function
    project.ProjectStatus.set_busy(project=project_obj, busy=False)
    assert not project_obj.busy


# post

def test_full_natural_project_life_cycle(module_client, boto3_session):
    """Verifies that the project status can do the following transitions:
    In Progress -> Available -> Expired -> Available --> Expired --> Available --> Expired --> Archived

    The project should be able to be extended twice, thus being in avaiable 3 times.
    """
    pass

def test_projectstatus_when_busy(module_client):
    """Status change should not be possible when project is busy."""
    # Get user
    username = "unitadmin"
    user = models.User.query.filter_by(username=username).one_or_none()
    assert user

    # Get project and set to busy
    project = user.projects[0]
    project.busy = True
    db.session.commit()
    assert project.busy

    # Attempt to change status
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS[username]).token(module_client),
        query_string={"project": project.public_id},
        json={"something": "something"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert (
        f"The status for the project '{project.public_id}' is already in the process of being changed."
        in response.json.get("message")
    )


def test_projectstatus_when_not_busy_but_invalid(module_client):
    """Status change which results in an exception should also reset busy to False."""
    # Get user
    username = "unitadmin"
    user = models.User.query.filter_by(username=username).one_or_none()
    assert user

    # Get project and set as not busy
    project = user.projects[0]
    project.busy = False
    db.session.commit()
    assert not project.busy

    # Attempt to change status
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS[username]).token(module_client),
        query_string={"project": project.public_id},
        json={"new_status": ""},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "No status transition provided. Specify the new status." in response.json.get("message")
    assert not project.busy


def test_projectstatus_submit_request_with_invalid_args(module_client, boto3_session):
    """Submit status request with invalid arguments"""
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    # Create project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={},
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing" in response.json["message"]

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={"new_status": "Invalid"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Invalid status" in response.json["message"]

    response: werkzeug.test.WrapperTestResponse = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={"test": "test"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "No status transition provided. Specify the new status." in response.json["message"]


def test_projectstatus_post_operationalerror(module_client, boto3_session):
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    new_status = {"new_status": "Deleted"}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client)
    with unittest.mock.patch("dds_web.db.session.commit", mock_sqlalchemyerror):
        # Run command
        response = module_client.post(
            tests.DDSEndpoint.PROJECT_STATUS,
            headers=token,
            query_string={"project": project_id},
            json=new_status,
        )
        assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR


def test_projectstatus_set_project_to_deleted_from_in_progress(module_client, boto3_session):
    """Create project and set status to deleted"""
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    new_status = {"new_status": "Deleted"}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    # add a file
    response = module_client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=FIRST_NEW_FILE,
    )

    assert file_in_db(test_dict=FIRST_NEW_FILE, project=project.id)

    for field, value in vars(project).items():
        if field in fields_set_to_null:
            assert value
    assert project.project_user_keys

    response = module_client.get(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
    )

    assert response.status_code == http.HTTPStatus.OK
    assert response.json["current_status"] == project.current_status

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Deleted"
    for field, value in vars(project).items():
        if field in fields_set_to_null:
            assert not value
    assert not project.project_user_keys


def test_projectstatus_archived_project(module_client, boto3_session):
    """Create a project and archive it"""
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")
    # add a file
    response = module_client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=FIRST_NEW_FILE,
    )

    project = project_row(project_id=project_id)

    assert file_in_db(test_dict=FIRST_NEW_FILE, project=project.id)

    new_status = {"new_status": "Archived"}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Archived"

    assert not max(project.project_statuses, key=lambda x: x.date_created).is_aborted
    assert not file_in_db(test_dict=FIRST_NEW_FILE, project=project.id)
    assert not project.project_user_keys

    for field, value in vars(project).items():
        if field in fields_set_to_null:
            assert value
    assert project.researchusers


def test_projectstatus_archived_project_db_fail(
    module_client, boto3_session, capfd: LogCaptureFixture
):
    """Create a project and archive it fails in DB update"""

    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    # change status and mock fail in DB operation
    mock_query = MagicMock()
    mock_query.filter.return_value.delete.side_effect = sqlalchemy.exc.OperationalError(
        "OperationalError", "test", "sqlalchemy"
    )
    with patch("dds_web.database.models.File.query", mock_query):
        new_status = {"new_status": "Archived"}
        response = module_client.post(
            tests.DDSEndpoint.PROJECT_STATUS,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
            query_string={"project": project_id},
            json=new_status,
        )
        assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR

    _, err = capfd.readouterr()
    assert "DeletionError" in err
    assert (
        "Project bucket contents were deleted, but they were not deleted from the database. Please contact SciLifeLab Data Centre"
        in err
    )

    assert project.is_active


def test_projectstatus_aborted_project(module_client, boto3_session):
    """Create a project and try to abort it"""
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")
    # add a file
    response = module_client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=FIRST_NEW_FILE,
    )

    project = project_row(project_id=project_id)

    assert file_in_db(test_dict=FIRST_NEW_FILE, project=project.id)

    for field, value in vars(project).items():
        if field in fields_set_to_null:
            assert value
    assert len(project.researchusers) > 0
    assert project.project_user_keys

    time.sleep(1)
    new_status = {"new_status": "Archived", "is_aborted": True}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Archived"
    assert max(project.project_statuses, key=lambda x: x.date_created).is_aborted
    assert not file_in_db(test_dict=FIRST_NEW_FILE, project=project.id)
    assert not project.project_user_keys

    for field, value in vars(project).items():
        if field in fields_set_to_null:
            assert not value
    assert len(project.researchusers) == 0


def test_projectstatus_abort_from_in_progress_once_made_available(module_client, boto3_session):
    """Create project and abort it from In Progress after it has been made available"""
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")

    # add a file
    response = module_client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=FIRST_NEW_FILE,
    )

    project = project_row(project_id=project_id)

    assert file_in_db(test_dict=FIRST_NEW_FILE, project=project.id)

    new_status = {"new_status": "Available"}
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"

    new_status["new_status"] = "In Progress"
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "In Progress"
    assert project.project_user_keys

    response = module_client.get(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={"history": True},
    )

    assert response.status_code == http.HTTPStatus.OK
    assert response.json["current_status"] == project.current_status
    assert response.json["current_deadline"]
    assert response.json["history"]

    time.sleep(1)
    new_status["new_status"] = "Archived"
    new_status["is_aborted"] = True
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Archived"
    assert max(project.project_statuses, key=lambda x: x.date_created).is_aborted
    assert not file_in_db(test_dict=FIRST_NEW_FILE, project=project.id)

    for field, value in vars(project).items():
        if field in fields_set_to_null:
            assert not value
    assert len(project.researchusers) == 0
    assert not project.project_user_keys


def test_projectstatus_check_invalid_transitions_from_in_progress(module_client, boto3_session):
    """Check all invalid transitions from In Progress"""
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    # In Progress to Expired
    new_status = {"new_status": "Expired"}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "In Progress"
    assert (
        "You cannot expire a project that has the current status 'In Progress'."
        in response.json["message"]
    )

    # In Progress to Archived
    new_status["new_status"] = "Archived"
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Archived"


def test_projectstatus_set_project_to_available_valid_transition(module_client, test_project):
    """Set status to Available for test project"""

    new_status = {"new_status": "Available", "deadline": 10}

    project_id = test_project
    project = project_row(project_id=project_id)
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"

    db_deadline = max(project.project_statuses, key=lambda x: x.date_created).deadline
    calc_deadline = datetime.datetime.utcnow().replace(
        hour=23, minute=59, second=59, microsecond=0
    ) + datetime.timedelta(days=new_status["deadline"])

    assert db_deadline == calc_deadline


def test_projectstatus_set_project_to_available_no_mail(module_client, boto3_session):
    """Set status to Available for test project, but skip sending mails"""
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=token,
        json=proj_data_with_existing_users,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json and response.json.get("user_addition_statuses")
    for x in response.json.get("user_addition_statuses"):
        assert "given access to the Project" in x

    public_project_id = response.json.get("project_id")

    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        with unittest.mock.patch.object(
            dds_web.api.user.AddUser, "compose_and_send_email_to_user"
        ) as mock_mail_func:
            response = module_client.post(
                tests.DDSEndpoint.PROJECT_STATUS,
                headers=token,
                query_string={"project": public_project_id},
                json={"new_status": "Available", "deadline": 10, "send_email": False},
            )
            # assert that no mail is being sent.
            assert mock_mail_func.called == False
        assert mock_mail_send.call_count == 0

    assert response.status_code == http.HTTPStatus.OK
    assert "An e-mail notification has not been sent." in response.json["message"]


def test_projectstatus_set_project_to_deleted_from_available(module_client, test_project):
    """Try to set status to Deleted for test project in Available"""

    new_status = {"new_status": "Deleted"}

    project_id = test_project
    project = project_row(project_id=project_id)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Available"


def test_projectstatus_check_deadline_remains_same_when_made_available_again_after_going_to_in_progress(
    module_client, test_project
):
    """Check deadline remains same when an available project goes to In Progress and is made available again"""
    project_id = test_project
    project = project_row(project_id=project_id)
    assert project.current_status == "Available"
    deadline_initial = project.current_deadline

    time.sleep(1)
    new_status = {"new_status": "In Progress"}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "In Progress"
    time.sleep(1)

    # Try to delete the project
    new_status = {"new_status": "Deleted"}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert (
        "You cannot delete a project that has been made available previously"
        in response.json["message"]
    )
    assert project.current_status == "In Progress"

    new_status = {"new_status": "Available"}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"
    assert project.current_deadline == deadline_initial


def test_projectstatus_set_project_to_expired_from_available(module_client, test_project):
    """Set status to Expired for test project"""

    new_status = {"new_status": "Expired", "deadline": 5}

    project_id = test_project
    project = project_row(project_id=project_id)
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Expired"

    db_deadline = max(project.project_statuses, key=lambda x: x.date_created).deadline
    calc_deadline = datetime.datetime.utcnow().replace(
        hour=23, minute=59, second=59, microsecond=0
    ) + datetime.timedelta(days=new_status["deadline"])

    assert db_deadline == calc_deadline


def test_projectstatus_project_availability_after_set_to_expired_more_than_twice(
    module_client, test_project
):
    """Try to set status to Available for test project after being in Expired 3 times.
    
    In Progress --> Available --> Expired --> Available --> Expired --> Available --> Expired --> Archived
    """
    
    # In Progress --> Available: Should succeed
    new_status = {"new_status": "Available", "deadline": 5}

    project_id = test_project
    project = project_row(project_id=project_id)
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"

    # Available --> Expired: Should succeed
    new_status["new_status"] = "Expired"
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Expired"

    # Expired --> Available (1st time): Should succeed
    new_status["new_status"] = "Available"
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"

    # Available --> Expired: Should succeed
    new_status["new_status"] = "Expired"
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Expired"

    # Expired --> Available (2nd time): Should succeed
    new_status["new_status"] = "Available"
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"

    # Available --> Expired: Should succeed
    new_status["new_status"] = "Expired"
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Expired"

    # Expired --> Available (3rd time): Should fail
    new_status["new_status"] = "Available"
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Expired"

    assert "Project cannot be made Available any more times" in response.json["message"]

def test_projectstatus_invalid_transitions_from_expired(module_client, test_project):
    """Check all invalid transitions from Expired"""

    # Expired to In progress
    new_status = {"new_status": "In Progress"}
    project_id = test_project
    project = project_row(project_id=project_id)
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Expired"
    assert (
        "You cannot retract a project that has the current status 'Expired'"
        in response.json["message"]
    )

    # Expired to Deleted
    new_status["new_status"] = "Deleted"
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Expired"
    assert (
        "You cannot delete a project that has the current status 'Expired'"
        in response.json["message"]
    )


def test_projectstatus_set_project_to_archived(module_client, test_project, boto3_session):
    """Archive an expired project"""

    new_status = {"new_status": "Archived"}
    project_id = test_project
    project = project_row(project_id=project_id)

    assert file_in_db(test_dict=FIRST_NEW_FILE, project=project.id)
    assert project.project_user_keys

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Archived"
    assert not max(project.project_statuses, key=lambda x: x.date_created).is_aborted
    assert not file_in_db(test_dict=FIRST_NEW_FILE, project=project.id)
    assert not project.project_user_keys
    assert not project.is_active


def test_projectstatus_invalid_transitions_from_archived(module_client, test_project):
    """Check all invalid transitions from Archived"""

    # Archived to In progress
    project_id = test_project
    project = project_row(project_id=project_id)

    new_status = {"new_status": "In Progress"}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Archived"
    assert "Cannot change status for a project" in response.json["message"]

    # Archived to Deleted
    new_status["new_status"] = "Deleted"
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Archived"
    assert "Cannot change status for a project" in response.json["message"]

    # Archived to Available
    new_status["new_status"] = "Available"
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Archived"
    assert "Cannot change status for a project" in response.json["message"]

    # Archived to Expired
    new_status["new_status"] = "Expired"
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=new_status,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Archived"
    assert "Cannot change status for a project" in response.json["message"]


def test_projectstatus_post_invalid_deadline_release(module_client, boto3_session):
    """Attempt to set an invalid deadline."""
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    # Release project - should fail due to invalid deadline
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={"new_status": "Available", "deadline": 100},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "The deadline needs to be less than (or equal to) 90 days." in response.json["message"]


def test_projectstatus_post_invalid_deadline_expire(module_client, boto3_session):
    # Create unit admins to allow project creation
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    # Release project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={"new_status": "Available"},
    )
    assert response.status_code == http.HTTPStatus.OK

    # Expire project - should fail due to invalid deadline
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={"new_status": "Expired", "deadline": 40},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "The deadline needs to be less than (or equal to) 30 days." in response.json["message"]


def test_extend_deadline_bad_confirmed(module_client, boto3_session):
    """Try to extend a deadline and send a not boolean for confirmation"""

    # create project and release it
    project_id, project = create_and_release_project(
        client=module_client, proj_data=proj_data, release_data=release_project
    )
    assert project.times_expired == 0
    time.sleep(1)  # tests are too fast

    # try to extend deadline with a string as confirmed - should fail
    response = module_client.patch(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={**extend_deadline_data, "confirmed": "true"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "`confirmed` is a boolean value: True or False." in response.json["message"]


def test_extend_deadline_no_confirmed(module_client, boto3_session):
    """Try to extend a deadline before confirmation - should sent a warning and no operation is perfrom"""

    # create project and release it
    project_id, project = create_and_release_project(
        client=module_client, proj_data=proj_data, release_data=release_project
    )
    assert project.times_expired == 0
    time.sleep(1)  # tests are too fast

    # try to extend deadline
    response = module_client.patch(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=extend_deadline_data_no_confirmed,
    )
    # status code is ok but no operation perform
    assert response.status_code == http.HTTPStatus.OK
    assert project.times_expired == 0

    assert "Operation must be confirmed before proceding." in response.json["warning"]
    assert all(
        item in response.json
        for item in ["project_info", "project_status", "warning", "default_unit_days"]
    )


def test_extend_deadline_when_busy(module_client, boto3_session):
    """Request should not be possible when project is busy."""

    # create project and release it
    project_id, project = create_and_release_project(
        client=module_client, proj_data=proj_data, release_data=release_project
    )
    assert project.times_expired == 0
    time.sleep(1)  # tests are too fast

    # set to busy
    project.busy = True
    db.session.commit()
    assert project.busy

    # attempt to extend deadline
    response = module_client.patch(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=extend_deadline_data,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    assert (
        f"The deadline for the project '{project_id}' is already in the process of being changed. "
        in response.json["message"]
    )
    assert (
        "Please try again later. \n\nIf you know that the project is not busy, contact support."
        in response.json["message"]
    )


def test_extend_deadline_no_deadline(module_client, boto3_session):
    """If no deadline has been provided it should not be executed anything"""

    # create project and release it
    project_id, project = create_and_release_project(
        client=module_client, proj_data=proj_data, release_data=release_project
    )
    assert project.times_expired == 0
    time.sleep(1)  # tests are too fast

    # try to extend deadline - no new deadline provided
    response = module_client.patch(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={"confirmed": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    assert project.times_expired == 0
    assert "Nothing to update." in response.json["message"]


def test_extend_deadline_project_not_available(module_client, boto3_session):
    """Is not possible to extend deadline to a project in another status than available."""

    # create a new project and never release it
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")

    # attempt to extend deadline - project is in progress
    response = module_client.patch(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=extend_deadline_data,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    assert (
        "You can only extend the deadline for a project that has the status 'Available'."
        in response.json["message"]
    )


def test_extend_deadline_too_much_days(module_client, boto3_session):
    """If the new deadline together with the time left already is more than 90 days it should not work"""

    # create project and release it with big dealdine
    project_id, project = create_and_release_project(
        client=module_client, proj_data=proj_data, release_data=release_project_big_deadline
    )
    assert project.times_expired == 0
    time.sleep(1)  # tests are too fast

    # try to extend deadline -> 80 + 11 > 90
    extend_deadline_data_big_deadline = {**extend_deadline_data, "new_deadline_in": 11}
    response = module_client.patch(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=extend_deadline_data_big_deadline,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert (
        "The new deadline needs to be less than (or equal to) 90 days." in response.json["message"]
    )


def test_extend_deadline_bad_new_deadline(module_client, boto3_session):
    """If the new deadlien provided is not an integer it should fail"""

    # create project and release it
    project_id, project = create_and_release_project(
        client=module_client, proj_data=proj_data, release_data=release_project
    )
    assert project.times_expired == 0
    time.sleep(1)  # tests are too fast

    # try to extend deadline with a bad new deadline
    extend_deadline_data_bad_deadline = {**extend_deadline_data, "new_deadline_in": "20"}
    response = module_client.patch(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=extend_deadline_data_bad_deadline,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert (
        "The deadline attribute passed should be of type Int (i.e a number)."
        in response.json["message"]
    )


def test_extend_deadline_more_than_default(module_client, boto3_session):
    """If the new deadline provided is more than the default unit days to release a project it should fail"""

    # create project and release it
    project_id, project = create_and_release_project(
        client=module_client, proj_data=proj_data, release_data=release_project_small_deadline
    )
    assert project.times_expired == 0
    time.sleep(1)  # tests are too fast

    default_unit_days = project.responsible_unit.days_in_available

    # try to extend deadline with a bigger deadline that it is suppose to have
    extend_deadline_data_bad_deadline = {
        **extend_deadline_data,
        "new_deadline_in": default_unit_days + 1,
    }
    response = module_client.patch(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=extend_deadline_data_bad_deadline,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert (
        "The number of days has to be lower than the default deadline extension number"
        in response.json["message"]
    )


def test_extend_deadline_maximum_number_available_exceeded(module_client, boto3_session):
    """A project should be able to be released once and extenced twice, thus in expired 3 times."""

    # create project and release it
    project_id, project = create_and_release_project(
        client=module_client, proj_data=proj_data, release_data=release_project_small_deadline
    )
    assert project.times_expired == 0
    deadline = project.current_deadline  # current deadline
    new_deadline_in = 1  # small new deadline

    for i in range(1, 5):
        time.sleep(1)  # tests are too fast

        # extend deadline by a small new deadline so we can do it several times
        extend_deadline_data_small_deadline = {
            **extend_deadline_data,
            "new_deadline_in": new_deadline_in,
        }
        response = module_client.patch(
            tests.DDSEndpoint.PROJECT_STATUS,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
            query_string={"project": project_id},
            json=extend_deadline_data_small_deadline,
        )
        if i < 4:
            assert response.status_code == http.HTTPStatus.OK
            assert project.times_expired == i
            assert project.current_deadline == deadline + datetime.timedelta(days=new_deadline_in)
            deadline = project.current_deadline  # update current deadline
            assert project.current_status == "Available"
            assert (
                f"The project '{project_id}' has been given a new deadline"
                in response.json["message"]
            )
            assert "An e-mail notification has not been sent." in response.json["message"]
        else:
            assert response.status_code == http.HTTPStatus.BAD_REQUEST
            assert (
                "Project availability limit: Project cannot be made Available any more times"
                in response.json["message"]
            )


def test_extend_deadline_ok(module_client, boto3_session):
    """Extend a project deadline of a project - it should work ok"""

    # create project and release it
    project_id, project = create_and_release_project(
        client=module_client, proj_data=proj_data, release_data=release_project_small_deadline
    )
    assert project.times_expired == 0
    time.sleep(1)  # tests are too fast

    deadline = project.current_deadline  # save current deadline

    # extend deadline
    response = module_client.patch(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json=extend_deadline_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert project.times_expired == 1
    assert project.current_deadline == deadline + datetime.timedelta(
        days=extend_deadline_data.get("new_deadline_in")
    )
    assert project.current_status == "Available"

    assert f"The project '{project_id}' has been given a new deadline" in response.json["message"]
    assert "An e-mail notification has not been sent." in response.json["message"]


def test_extend_deadline_mock_database_error(
    module_client, boto3_session, capfd: LogCaptureFixture
):
    """Operation fails when trying to save in the Database"""

    project_id, project = create_and_release_project(
        client=module_client, proj_data=proj_data, release_data=release_project_small_deadline
    )
    assert project.times_expired == 0
    time.sleep(1)  # tests are too fast

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client)

    with unittest.mock.patch.object(db.session, "rollback") as rollback:
        with unittest.mock.patch("dds_web.db.session.commit") as mock_commit:
            # we need this because the first time the commit function is called is when set_busy()
            def side_effect_generator():
                yield None  # First call, no exception
                while True:
                    yield sqlalchemy.exc.SQLAlchemyError()  # Subsequent calls, exception

            mock_commit.side_effect = side_effect_generator()

            # extend deadline
            response = module_client.patch(
                tests.DDSEndpoint.PROJECT_STATUS,
                headers=token,
                query_string={"project": project_id},
                json=extend_deadline_data,
            )
            assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Saving database changes failed." in response.json["message"]

    assert rollback.called
    _, err = capfd.readouterr()
    assert "Failed to extend deadline" in err


def test_projectstatus_post_deletion_and_archivation_errors(module_client, boto3_session):
    """Mock the different expections that can occur when deleting project."""
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    for func in [mock_typeerror, mock_databaseerror, mock_deletionerror, mock_bucketnotfounderror]:
        with unittest.mock.patch("dds_web.api.project.ProjectStatus.delete_project_info", func):
            response = module_client.post(
                tests.DDSEndpoint.PROJECT_STATUS,
                headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
                query_string={"project": project_id},
                json={"new_status": "Deleted"},
            )
            assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Server Error: Status was not updated" in response.json["message"]
            assert project.is_active


def test_projectstatus_failed_delete_project_content(module_client, boto3_session):
    """Mock the different expections that can occur when deleting project."""
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    for func in [
        mock_deletionerror,
        mock_sqlalchemyerror,
        mock_operationalerror,
        mock_attributeerror,
    ]:
        with unittest.mock.patch(
            "dds_web.api.project.RemoveContents.delete_project_contents", func
        ):
            response = module_client.post(
                tests.DDSEndpoint.PROJECT_STATUS,
                headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
                query_string={"project": project_id},
                json={"new_status": "Deleted"},
            )
            assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Server Error: Status was not updated" in response.json["message"]
            assert project.is_active


def test_projectstatus_failed_rm_project_user_keys(module_client, boto3_session):
    """Mock the different expections that can occur when deleting project."""
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    for func in [mock_sqlalchemyerror, mock_operationalerror]:
        with unittest.mock.patch("dds_web.api.project.ProjectStatus.rm_project_user_keys", func):
            response = module_client.post(
                tests.DDSEndpoint.PROJECT_STATUS,
                headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
                query_string={"project": project_id},
                json={"new_status": "Deleted"},
            )
            assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Server Error: Status was not updated" in response.json["message"]
            assert project.is_active


def test_projectstatus_post_archiving_without_aborting(module_client, boto3_session):
    """Try to archive a project thas has been available."""
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    # Release project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={"new_status": "Available"},
    )
    assert response.status_code == http.HTTPStatus.OK

    time.sleep(1)  # tests are too fast

    # Retract project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={"new_status": "In Progress"},
    )
    assert response.status_code == http.HTTPStatus.OK

    # Retract project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={"new_status": "Archived"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert (
        "You cannot archive a project that has been made available previously"
        in response.json["message"]
    )


def test_projectstatus_released_post_deletion_and_archivation_errors(module_client, boto3_session):
    """Mock the different expections that can occur when deleting project."""
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    # Release project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        json={"new_status": "Available"},
    )
    assert response.status_code == http.HTTPStatus.OK

    for func in [mock_typeerror, mock_databaseerror, mock_deletionerror, mock_bucketnotfounderror]:
        with unittest.mock.patch("dds_web.api.project.ProjectStatus.delete_project_info", func):
            response = module_client.post(
                tests.DDSEndpoint.PROJECT_STATUS,
                headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
                query_string={"project": project_id},
                json={"new_status": "Archived", "is_aborted": True},
            )
            assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Server Error: Status was not updated" in response.json["message"]
            assert project.is_active


# GetPublic


def test_getpublic_publickey_is_none(module_client, boto3_session):
    """Try to get public key from project that does not have a project public key."""
    # Ensure enough unit admins
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    # Create project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    # Remove public key
    project.public_key = None
    db.session.commit()

    # Get public key - does not exist so it fails
    response = module_client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        query_string={"project": project_id},
    )
    assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
    assert "Unrecoverable key error. Aborting." in response.json["message"]


def test_getpublic_publickey(module_client, boto3_session):
    """Get project public key."""
    # Ensure enough unit admins
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    if current_unit_admins < 3:
        create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    # Create project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    # Get public key
    response = module_client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        query_string={"project": project_id},
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json

    # Verify correct
    public_key = response_json.get("public")
    assert public_key and public_key == project.public_key.hex().upper()


def test_proj_public_no_project(module_client):
    """Attempting to get public key without a project should not work"""
    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(module_client)
    response = module_client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert "Missing required information: 'project'" in response_json.get("message")


def test_project_public_researcher_get(module_client):
    """User should get access to public key"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(module_client)
    response = module_client.get(
        tests.DDSEndpoint.PROJ_PUBLIC, query_string={"project": "public_project_id"}, headers=token
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("public")


def test_project_public_facility_put(module_client):
    """User should get access to public key"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client)
    response = module_client.get(
        tests.DDSEndpoint.PROJ_PUBLIC, query_string={"project": "public_project_id"}, headers=token
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("public")


# ProjectBusy


def test_set_busy_no_token(module_client):
    """Token required to set project busy/not busy."""
    response = module_client.put(tests.DDSEndpoint.PROJECT_BUSY, headers=tests.DEFAULT_HEADER)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    assert response.json.get("message")
    assert "No token" in response.json.get("message")


def test_set_busy_invalid_version(module_client):
    """ProjectBusy endpoint is empty and should only return error message about invalid version."""
    # Error messages
    major_version_error: str = "You're using an old CLI version, please upgrade to the latest one."
    busy_error: str = (
        "Your CLI version is trying to use functionality which is no longer in use. Upgrade your version to the latest one and run your command again."
    )

    for username in ["superadmin", "researchuser", "projectowner", "unituser", "unitadmin"]:
        # Get user
        user = models.User.query.filter_by(username=username).one_or_none()
        assert user

        # Get project
        project = user.projects[0]
        assert project

        # Authenticate and run
        token = tests.UserAuth(tests.USER_CREDENTIALS[username]).token(module_client)
        for version, error_message in {
            token["X-CLI-Version"]: busy_error,
            "1.9.9": major_version_error,
            "2.1.9": busy_error,
        }.items():
            token["X-CLI-Version"] = version
            response = module_client.put(
                tests.DDSEndpoint.PROJECT_BUSY,
                headers=token,
                query_string={"project": project.public_id},
                json={"something": "notabool"},
            )
            assert response.status_code == http.HTTPStatus.FORBIDDEN
            assert error_message in response.json.get("message")


# Project usage


def test_project_usage(module_client):
    """Test if correct cost value is returned."""

    cost_gbhour = 0.09 / (30 * 24)

    # Get user and project
    user = models.User.query.filter_by(username="unitadmin").one_or_none()
    assert user
    project_0 = user.projects[0]
    assert project_0

    # Call project_usage() for the project and check if cost is calculated correctly
    proj_bhours, proj_cost = UserProjects.project_usage(project=project_0)
    assert (proj_bhours / 1e9) * cost_gbhour == proj_cost


def test_email_project_release(module_client, boto3_session):
    """Test that check that the email sent to the researchers when project is released is correct"""
    public_project_id = "public_project_id"

    create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins >= 3

    # user to perfrom the operation
    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client)
    # project to be released
    project = models.Project.query.filter_by(public_id=public_project_id).first()
    # num of researchers that will receive email
    num_users = models.ProjectUsers.query.filter_by(project_id=project.id).count()

    # Release project and check email
    with mail.record_messages() as outbox:
        response = module_client.post(
            tests.DDSEndpoint.PROJECT_STATUS,
            headers=token,
            query_string={"project": public_project_id},
            json={"new_status": "Available", "deadline": 10, "send_email": True},
        )
        assert len(outbox) == num_users  # nº of Emails informing researchers
        assert "Project made available by" in outbox[-1].subject

        body = outbox[-1].body  # plain text
        html = outbox[-1].html

        project_title = project.title

        ## check plain text message
        assert f"- Project Title: {project_title}" in body
        assert f"- DDS project ID: {public_project_id}" in body
        assert f"dds ls -p {public_project_id}" in body
        assert f"dds data get -p {public_project_id} -a --verify-checksum" in body
        assert "If you experience issues, please contact the SciLifeLab unit" in body
        assert (
            "What is the DDS? The DDS is a system for SciLifeLab infrastructures to deliver data to researchers in a fast, secure and simple way"
            in body
        )

        ## check html
        assert f"<li><b>Project Title:</b> {project_title}</li>" in html
        assert f"<li><b>DDS project ID:</b> {public_project_id}</li>" in html
        assert f"dds ls -p {public_project_id}" in html
        assert f"dds data get -p {public_project_id} -a --verify-checksum" in html
        assert "If you experience issues, please contact the SciLifeLab unit" in html
        assert (
            "<b>What is the DDS?</b> The DDS is a system for SciLifeLab infrastructures to deliver data to researchers in a fast, secure and simple way."
            in html
        )

    assert response.status_code == http.HTTPStatus.OK
