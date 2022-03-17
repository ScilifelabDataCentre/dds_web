# Installed
import json
import http
import copy

# Own
import tests
from tests.test_project_creation import proj_data_with_existing_users, create_unit_admins
from dds_web.database import models


def test_remove_user_from_project(client, boto3_session):
    """Remove an associated user from a project"""

    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_with_existing_users,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")
    email = proj_data_with_existing_users["users_to_add"][0]["email"]
    rem_user = {"email": email}
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project_id},
        json=rem_user,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert (
        f"User with email {email} no longer associated with {project_id}."
        in response.json["message"]
    )


def test_remove_not_associated_user_from_project(client, boto3_session):
    """Try to remove a user that exists in db but is not associated to a project"""
    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    proj_data = copy.deepcopy(proj_data_with_existing_users)
    proj_data["users_to_add"].pop(1)

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")

    email = proj_data_with_existing_users["users_to_add"][1]["email"]
    rem_user = {"email": email}
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project_id},
        json=rem_user,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Cannot remove non-existent project access" in response.json["message"]


def test_remove_nonexistent_user_from_project(client, boto3_session):
    """Try to remove an nonexistent user from a project"""

    create_unit_admins(num_admins=2)

    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_with_existing_users,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")
    email = "nonexistent@testmail.com"
    rem_user = {"email": email}
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project_id},
        json=rem_user,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Cannot remove non-existent project access" in response.json["message"]


def test_remove_existing_user_from_nonexistent_proj(client, boto3_session):
    """Try to an existing user from a nonexistent project"""

    project_id = "nonexistent001"
    email = proj_data_with_existing_users["users_to_add"][0]["email"]
    rem_user = {"email": email}

    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project_id},
        json=rem_user,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "The specified project does not exist" in response.json["message"]
