# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import json
import pytest
import datetime
import time
import unittest.mock

# Installed
import boto3
import flask_mail

# Own
import dds_web
import tests
from tests.test_files_new import project_row, file_in_db, FIRST_NEW_FILE
from tests.test_project_creation import proj_data_with_existing_users, create_unit_admins
from dds_web.database import models

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


def test_submit_request_with_invalid_args(module_client, boto3_session):
    """Submit status request with invalid arguments"""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

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


def test_set_project_to_deleted_from_in_progress(module_client, boto3_session):
    """Create project and set status to deleted"""
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

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


def test_archived_project(module_client, boto3_session):
    """Create a project and archive it"""
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

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


def test_aborted_project(module_client, boto3_session):
    """Create a project and try to abort it"""
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

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


def test_abort_from_in_progress_once_made_available(module_client, boto3_session):
    """Create project and abort it from In Progress after it has been made available"""
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

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


def test_check_invalid_transitions_from_in_progress(module_client, boto3_session):
    """Check all invalid transitions from In Progress"""
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

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


def test_set_project_to_available_valid_transition(module_client, test_project):
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


def test_set_project_to_available_no_mail(module_client, boto3_session):
    """Set status to Available for test project, but skip sending mails"""
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

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


def test_set_project_to_deleted_from_available(module_client, test_project):
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


def test_check_deadline_remains_same_when_made_available_again_after_going_to_in_progress(
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


def test_set_project_to_expired_from_available(module_client, test_project):
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


def test_project_availability_after_set_to_expired_more_than_twice(module_client, test_project):
    """Try to set status to Available for test project after being in Expired 3 times"""

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


def test_invalid_transitions_from_expired(module_client, test_project):
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


def test_set_project_to_archived(module_client, test_project, boto3_session):
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


def test_invalid_transitions_from_archived(module_client, test_project):
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
