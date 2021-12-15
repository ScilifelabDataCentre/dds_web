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

# Own
import tests
from tests.test_files_new import project_row

# CONFIG ################################################################################## CONFIG #

proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}


@pytest.fixture(scope="module")
def test_project(module_client):
    """Create a shared test project"""
    with unittest.mock.patch.object(boto3.session.Session, "resource") as mock_session:
        response = module_client.post(
            tests.DDSEndpoint.PROJECT_CREATE,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
            data=json.dumps(proj_data),
            content_type="application/json",
        )

    return response.json.get("project_id")


def test_set_project_to_deleted_from_in_progress(module_client, boto3_session):
    """Create project and set status to deleted"""

    new_status = {"new_status": "Deleted"}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Deleted"


def test_aborted_project(module_client, boto3_session):
    """Create a project and try to abort it"""

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")
    project = project_row(project_id=project_id)

    new_status = {"new_status": "Archived"}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "In Progress"
    assert "Invalid status transition" in response.json["message"]

    new_status["new_status"] = "Available"
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"

    time.sleep(1)
    new_status["new_status"] = "Archived"
    new_status["is_aborted"] = True
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Archived"
    assert max(project.project_statuses, key=lambda x: x.date_created).is_aborted


def test_check_invalid_transitions_from_in_progress(module_client, test_project):
    """Check all invalid transitions from In Progress"""

    project_id = test_project
    project = project_row(project_id=project_id)

    # In Progress to Expired
    new_status = {"new_status": "Expired"}
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "In Progress"
    assert "Invalid status transition" in response.json["message"]

    # In Progress to Archived
    new_status["new_status"] = "Archived"
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "In Progress"
    assert "Invalid status transition" in response.json["message"]


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
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"

    db_deadline = max(project.project_statuses, key=lambda x: x.date_created).deadline
    calc_deadline = datetime.datetime.now().replace(
        hour=23, minute=59, second=59, microsecond=0
    ) + datetime.timedelta(days=new_status["deadline"])

    assert db_deadline == calc_deadline


def test_set_project_to_deleted_from_available(module_client, test_project):
    """Try to set status to Deleted for test project in Available"""

    new_status = {"new_status": "Deleted"}

    project_id = test_project
    project = project_row(project_id=project_id)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Available"


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
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Expired"

    db_deadline = max(project.project_statuses, key=lambda x: x.date_created).deadline
    calc_deadline = datetime.datetime.now().replace(
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
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"

    new_status["new_status"] = "Expired"
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Expired"

    new_status["new_status"] = "Available"
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"

    new_status["new_status"] = "Expired"
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Expired"

    new_status["new_status"] = "Available"
    time.sleep(1)

    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
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
        data=json.dumps(new_status),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Expired"
    assert "Invalid status transition" in response.json["message"]

    # Expired to Deleted
    new_status["new_status"] = "Deleted"
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Expired"
    assert "Invalid status transition" in response.json["message"]


def test_set_project_to_archived(module_client, test_project, boto3_session):
    """Archive an expired project"""

    new_status = {"new_status": "Archived"}
    project_id = test_project
    project = project_row(project_id=project_id)
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Archived"
    assert not max(project.project_statuses, key=lambda x: x.date_created).is_aborted


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
        data=json.dumps(new_status),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Archived"
    assert "Invalid status transition" in response.json["message"]

    # Archived to Deleted
    new_status["new_status"] = "Deleted"
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Archived"
    assert "Invalid status transition" in response.json["message"]

    # Archived to Available
    new_status["new_status"] = "Available"
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Archived"
    assert "Invalid status transition" in response.json["message"]

    # Archived to Expired
    new_status["new_status"] = "Expired"
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "Archived"
    assert "Invalid status transition" in response.json["message"]
