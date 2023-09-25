# Installed
import http
import copy

# Own
import tests
from tests.test_project_creation import proj_data_with_existing_users, create_unit_admins
from dds_web.database import models

# CONFIG ################################################################################## CONFIG #

# proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}
proj_query = {"project": "public_project_id"}
# proj_query_restricted = {"project": "restricted_project_id"}
first_new_email = {"email": "first_test_email@mailtrap.io"}
first_new_user = {**first_new_email, "role": "Researcher"}

# TESTS ################################################################################## TEST #


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


def test_remove_nonacepted_user_from_other_project(client, boto3_session):
    """Try to remove an User with an unacepted invite from another project should result in an error"""

    create_unit_admins(num_admins=2)
    current_unit_admins = models.UnitUser.query.filter_by(unit_id=1, is_admin=True).count()
    assert current_unit_admins == 3

    # create a new project
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=proj_data_with_existing_users,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")

    # invite a new user to an existing project
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": "public_project_id"},
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    # try to remove the user from the first project
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project_id},
        json=first_new_user,
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


def test_researcher_removes_project_owner(client):
    """
    A Researcher who is not a PO should not be able to delete a PO
    """

    project_id = "public_project_id"
    email = "projectowner@mailtrap.io"

    rem_user = {"email": email}
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": project_id},
        json=rem_user,
    )

    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "You do not have the necessary permissions" in response.json["message"]


def test_user_personal_removed(client):
    """
    User  personal cannot be deleted from individual projects (they should be removed from the unit)
    """

    project_id = "public_project_id"
    email = "unituser2@mailtrap.io"

    rem_user = {"email": email}
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project_id},
        json=rem_user,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    # Should give error because a unit personal cannot be granted access to individual projects
    assert "Cannot remove non-existent project access." in response.json["message"]

def test_removed_myself(client):
    """
    An User cannot remove themselves from a project
    """

    project_id = "public_project_id"
    email = "projectowner@mailtrap.io"

    rem_user = {"email": email}
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client),
        query_string={"project": project_id},
        json=rem_user,
    )

    assert response.status_code == http.HTTPStatus.FORBIDDEN
    # Should give error because a unit personal cannot be granted access to individual projects
    assert "You cannot renew your own access." in response.json["message"]




