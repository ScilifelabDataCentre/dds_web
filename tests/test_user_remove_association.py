# Installed
import http
import copy

# Own
import tests
from tests.test_project_creation import proj_data_with_existing_users, create_unit_admins
from dds_web.database import models
from tests.test_project_access import invite_to_project, get_existing_projects

# CONFIG ################################################################################## CONFIG #

# proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}
proj_query = {"project": "public_project_id"}
# proj_query_restricted = {"project": "restricted_project_id"}
first_new_email = {"email": "first_test_email@mailtrap.io"}
first_new_user = {**first_new_email, "role": "Researcher"}
first_new_user_unit_admin = {**first_new_email, "role": "Unit Admin"}
first_new_user_unit_personel = {**first_new_email, "role": "Unit Personnel"}

remove_user_project_owner = {"email": "projectowner@mailtrap.io"}
remove_user_unit_user = {"email": "unituser2@mailtrap.io"}
remove_user_project_owner = {"email": "projectowner@mailtrap.io"}


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

    projects = get_existing_projects()
    project_1 = projects[0]
    project_2 = projects[1]

    # invite a new user to a project
    invite_to_project(project=project_1, client=client, json_query=first_new_user)

    # try to remove the same user from a different one
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project_2.public_id},
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

    # Research user trying to delete PO
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string=proj_query,
        json=remove_user_project_owner,
    )

    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "Insufficient credentials" in response.json["message"]


def test_user_personal_removed(client):
    """
    User  personal cannot be deleted from individual projects (they should be removed from the unit instead)
    """

    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string=proj_query,
        json=remove_user_unit_user,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    # Should give error because a unit personal cannot be granted access to individual projects
    assert "Cannot remove non-existent project access." in response.json["message"]


def test_removed_myself(client):
    """
    An User cannot remove themselves from a project
    """

    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client),
        query_string=proj_query,
        json=remove_user_project_owner,
    )

    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "You cannot revoke your own access" in response.json["message"]


def test_remove_invite_unit_admin(client):
    """
    A project removal request for an unanswered invite of unit admin should not work
    """

    # invite a new unit admin to the system
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=first_new_user_unit_admin,
    )
    assert response.status_code == http.HTTPStatus.OK

    # try to remove the unitadmin for a specific project within their unit -> should not work
    email = first_new_user_unit_admin["email"]
    rem_user = {"email": email}
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string=proj_query,
        json=rem_user,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    # Should give error because a unit personal cannot be granted access to individual projects
    assert (
        "Cannot remove a Unit Admin / Unit Personnel from individual projects"
        in response.json["message"]
    )


def test_invite_unit_user(client):
    """
    A project removal request for an unanswered invite of unit personel should not work
    """

    # invite a new unit user to the system
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=first_new_user_unit_personel,
    )
    assert response.status_code == http.HTTPStatus.OK

    # try to remove the unit personal for a specific project within their unit -> should not work
    email = first_new_user_unit_personel["email"]
    rem_user = {"email": email}
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string=proj_query,
        json=rem_user,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    # Should give error because a unit personal cannot be granted access to individual projects
    assert (
        "Cannot remove a Unit Admin / Unit Personnel from individual projects"
        in response.json["message"]
    )
