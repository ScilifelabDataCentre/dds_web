# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import datetime
import json
import unittest
import time
import os

# Installed
import pytest
import marshmallow

# Own
from dds_web import db
from dds_web.database import models
import tests


# CONFIG ################################################################################## CONFIG #

proj_data = {
    "pi": "researchuser@mailtrap.io",
    "title": "Test proj",
    "description": "A longer project description",
}
proj_data_with_existing_users = {
    **proj_data,
    "users_to_add": [
        {"email": "researchuser@mailtrap.io", "role": "Project Owner"},
        {"email": "researchuser2@mailtrap.io", "role": "Researcher"},
    ],
}
proj_data_with_nonexisting_users = {
    **proj_data,
    "users_to_add": [
        {"email": "non_existing_user@mailtrap.io", "role": "Project Owner"},
        {"email": "non_existing_user2@mailtrap.io", "role": "Researcher"},
    ],
}
proj_data_with_unsuitable_user_roles = {
    **proj_data,
    "users_to_add": [
        {"email": "researchuser@mailtrap.io", "role": "Unit Admin"},
        {"email": "researchuser2@mailtrap.io", "role": "Unit Personnel"},
    ],
}


def create_unit_admins(num_admins, unit_id=1):
    new_admins = []
    for i in range(1, num_admins + 1):
        new_admins.append(
            models.UnitUser(
                **{
                    "username": "unit_admin_" + os.urandom(4).hex(),
                    "name": "Unit Admin " + str(i),
                    "password": "password",
                    "is_admin": True,
                    "unit_id": unit_id,
                }
            )
        )

    db.session.add_all(new_admins)
    db.session.commit()


# TESTS #################################################################################### TESTS #


def test_create_project_too_few_unit_admins(client):
    """There needs to be at least 2 Unit Admins."""
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    response_json = response.json
    assert response_json
    assert "Your unit does not have enough Unit Admins" in response_json.get("message")


def test_create_project_two_unit_admins(client):
    """There needs to be at least 2 Unit Admins."""
    create_unit_admins(num_admins=1)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 2

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json
    assert "Your unit only has 2 Unit Admins" in response_json.get("warning")


def test_create_project_two_unit_admins_force(client):
    """The force option (not in cli) can be used to create a project even if there are
    less than 3 Unit Admins."""
    create_unit_admins(num_admins=1)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 2

    # Use force
    updated_proj_data = proj_data.copy()
    updated_proj_data["force"] = True
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=updated_proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    created_proj = models.Project.query.filter_by(
        created_by="unitadmin",
        title=updated_proj_data["title"],
        pi=updated_proj_data["pi"],
        description=updated_proj_data["description"],
    ).one_or_none()
    assert created_proj


def test_create_project_two_unit_admins_force(client):
    """The force option (not in cli) can be used to create a project even if there are
    less than 3 Unit Admins."""
    create_unit_admins(num_admins=1)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 2

    # Use force
    updated_proj_data = proj_data.copy()
    updated_proj_data["force"] = "not correct"
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=updated_proj_data,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    created_proj = models.Project.query.filter_by(
        created_by="unitadmin",
        title=updated_proj_data["title"],
        pi=updated_proj_data["pi"],
        description=updated_proj_data["description"],
    ).one_or_none()
    assert not created_proj


def test_create_project_empty(client):
    """Make empty request."""
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert response_json
    assert "Required data missing from request" in response_json.get("message")


def test_create_project_unknown_field(client):
    """Make request with unknown field passed."""
    # Make sure there's 3 unit admins for unit
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    # Attempt creating project
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json={"test": "test"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert (
        response_json
        and "title" in response_json
        and response_json["title"].get("message") == "Title is required."
    )


def test_create_project_missing_title(client):
    """Make request with missing title."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_no_title = proj_data.copy()
    proj_data_no_title.pop("title")

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=proj_data_no_title,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert (
        "title" in response_json and response_json["title"].get("message") == "Title is required."
    )


def test_create_project_none_title(client):
    """Make request with missing title."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_none_title = proj_data.copy()
    proj_data_none_title["title"] = None

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=proj_data_none_title,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert (
        "title" in response_json and response_json["title"].get("message") == "Title is required."
    )


def test_create_project_no_description(client):
    """Make request with missing title."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_no_description = proj_data.copy()
    proj_data_no_description.pop("description")

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=proj_data_no_description,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert (
        "description" in response_json
        and response_json["description"].get("message") == "A project description is required."
    )


def test_create_project_none_description(client):
    """Make request with missing title."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_none_description = proj_data.copy()
    proj_data_none_description["description"] = None

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=proj_data_none_description,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert (
        "description" in response_json
        and response_json["description"].get("message") == "A project description is required."
    )


def test_create_project_no_pi(client):
    """Make request with missing title."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_no_pi = proj_data.copy()
    proj_data_no_pi.pop("pi")

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=proj_data_no_pi,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert (
        "pi" in response_json
        and response_json["pi"].get("message") == "A principal investigator is required."
    )


def test_create_project_none_pi(client):
    """Make request with missing title."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_none_pi = proj_data.copy()
    proj_data_none_pi["pi"] = None

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=proj_data_none_pi,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert (
        "pi" in response_json
        and response_json["pi"].get("message") == "A principal investigator is required."
    )


def test_create_project_without_credentials(client):
    """Create project without valid user credentials."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    created_proj = models.Project.query.filter_by(
        created_by="researchuser",
        title=proj_data["title"],
        pi=proj_data["pi"],
        description=proj_data["description"],
    ).one_or_none()
    assert created_proj is None


def test_create_project_with_credentials(client, boto3_session):
    """Create project with correct credentials."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    time_before_run = datetime.datetime.utcnow()
    time.sleep(1)
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    created_proj = models.Project.query.filter_by(
        created_by="unituser",
        title=proj_data["title"],
        pi=proj_data["pi"],
        description=proj_data["description"],
    ).one_or_none()
    assert (
        created_proj
        and created_proj.date_created > time_before_run
        and not created_proj.non_sensitive
    )


def test_create_project_no_title(client):
    """Create project without a title specified."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json={"pi": "piName"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    created_proj = models.Project.query.filter_by(
        created_by="unituser",
        pi=proj_data["pi"],
    ).one_or_none()
    assert created_proj is None


def test_create_project_title_too_short(client):
    """Create a project with too short title."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_short_title = proj_data.copy()
    proj_data_short_title["title"] = ""
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_short_title,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    created_proj = models.Project.query.filter_by(
        created_by="unituser",
        title=proj_data_short_title["title"],
        pi=proj_data_short_title["pi"],
        description=proj_data_short_title["description"],
    ).one_or_none()
    assert not created_proj


def test_create_project_with_malformed_json(client):
    """Create a project with malformed project info."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json="",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    created_proj = models.Project.query.filter_by(
        created_by="unituser",
        title="",
        pi="",
        description="",
    ).one_or_none()
    assert created_proj is None


def test_create_project_sensitive(client, boto3_session):
    """Create a sensitive project."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    p_data = proj_data
    p_data["non_sensitive"] = False
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=p_data,
    )
    assert response.status_code == http.HTTPStatus.OK
    created_proj = models.Project.query.filter_by(
        created_by="unituser",
        title=proj_data["title"],
        pi=proj_data["pi"],
        description=proj_data["description"],
    ).one_or_none()
    assert created_proj and not created_proj.non_sensitive


def test_create_project_description_too_short(client):
    """Create a project with too short description."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_short_description = proj_data.copy()
    proj_data_short_description["description"] = ""
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_short_description,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    created_proj = models.Project.query.filter_by(
        created_by="unituser",
        title=proj_data_short_description["title"],
        pi=proj_data_short_description["pi"],
        description=proj_data_short_description["description"],
    ).one_or_none()
    assert not created_proj


def test_create_project_pi_too_short(client):
    """Create a project with too short PI."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_short_pi = proj_data.copy()
    proj_data_short_pi["pi"] = ""
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_short_pi,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    created_proj = models.Project.query.filter_by(
        created_by="unituser",
        title=proj_data_short_pi["title"],
        pi=proj_data_short_pi["pi"],
        description=proj_data_short_pi["description"],
    ).one_or_none()
    assert not created_proj


def test_create_project_pi_too_long(client):
    """Create a project with too long PI."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_long_pi = proj_data.copy()
    proj_data_long_pi["pi"] = "pi" * 128
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_long_pi,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    created_proj = models.Project.query.filter_by(
        created_by="unituser",
        title=proj_data_long_pi["title"],
        pi=proj_data_long_pi["pi"],
        description=proj_data_long_pi["description"],
    ).one_or_none()
    assert not created_proj


def test_create_project_wrong_status(client, boto3_session):
    """Create a project with own status, should be overridden."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_wrong_status = proj_data.copy()
    proj_data_wrong_status["status"] = "Incorrect Status"
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_wrong_status,
    )
    assert response.status_code == http.HTTPStatus.OK

    created_proj = models.Project.query.filter_by(
        created_by="unituser",
        title=proj_data_wrong_status["title"],
        pi=proj_data_wrong_status["pi"],
        description=proj_data_wrong_status["description"],
    ).one_or_none()
    assert created_proj and created_proj.current_status == "In Progress"


def test_create_project_sensitive_not_boolean(client):
    """Create project with incorrect non_sensitive format."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_sensitive_not_boolean = proj_data.copy()
    proj_data_sensitive_not_boolean["non_sensitive"] = "test"
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_sensitive_not_boolean,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    created_proj = models.Project.query.filter_by(
        created_by="unituser",
        title=proj_data_sensitive_not_boolean["title"],
        pi=proj_data_sensitive_not_boolean["pi"],
        description=proj_data_sensitive_not_boolean["description"],
    ).one_or_none()
    assert not created_proj


def test_create_project_date_created_overridden(client, boto3_session):
    """Create project with own date_created, should be overridden."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data_date_created_own = proj_data.copy()
    proj_data_date_created_own["date_created"] = "test"
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_date_created_own,
    )
    assert response.status_code == http.HTTPStatus.OK

    created_proj = models.Project.query.filter_by(
        created_by="unituser",
        title=proj_data_date_created_own["title"],
        pi=proj_data_date_created_own["pi"],
        description=proj_data_date_created_own["description"],
    ).one_or_none()
    assert created_proj and created_proj.date_created != proj_data_date_created_own["date_created"]


def test_create_project_with_users(client, boto3_session):
    """Create project and add users to the project."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_with_existing_users,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json and response.json.get("user_addition_statuses")
    for x in response.json.get("user_addition_statuses"):
        assert "given access to the Project" in x

    resp_json = response.json
    created_proj = models.Project.query.filter_by(public_id=resp_json["project_id"]).one_or_none()
    assert created_proj
    users = models.ProjectUsers.query.filter_by(project_id=created_proj.id).all()
    users_dict_from_db = []

    for user in users:
        users_dict_from_db.append({"username": user.user_id, "owner": user.owner})

    users_dict_from_email = []
    for user in proj_data_with_existing_users["users_to_add"]:
        email = models.Email.query.filter_by(email=user["email"]).one_or_none()
        users_dict_from_email.append(
            {
                "username": email.user_id,
                "owner": True if user.get("role") == "Project Owner" else False,
            }
        )

    case = unittest.TestCase()
    case.assertCountEqual(users_dict_from_db, users_dict_from_email)


def test_create_project_with_invited_users(client, boto3_session):
    """Create project and invite users to the project."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_with_nonexisting_users,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json and response.json.get("user_addition_statuses")
    for x in response.json.get("user_addition_statuses"):
        assert "Invitation sent" in x


def test_create_project_with_unsuitable_roles(client, boto3_session):
    """Create project and add users with unsuitable roles to the project."""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_with_unsuitable_user_roles,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json and response.json.get("user_addition_statuses")
    for x in response.json.get("user_addition_statuses"):
        assert "User Role should be either 'Project Owner' or 'Researcher'" in x
