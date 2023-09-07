# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import unittest

# Own
from dds_web import db
from dds_web.database import models
import tests


# CONFIG ################################################################################## CONFIG #

proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}
proj_query = {"project": "public_project_id"}
proj_query_restricted = {"project": "restricted_project_id"}

# TESTS #################################################################################### TESTS #


def test_list_proj_no_token(client):
    """Token required to list projects"""

    response = client.get(tests.DDSEndpoint.LIST_PROJ, headers=tests.DEFAULT_HEADER)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "No token" in response_json.get("message")


def test_deleted_user_when_listing_projects
    """ Deleted users that created a project should be listed as 'Former User' """

    token_unituser = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    token_unitadmin = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    
    # 1st Create project
    response = module_client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=token,
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    # next, delete the user that created it

    email_to_delete = "unituser1@mailtrap.io"
    test.create_delete_request(email_to_delete)
    token_delete = test.get_deletion_token(email_to_delete)

    client = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).fake_web_login(client)

    response = client.get(
        tests.DDSEndpoint.USER_CONFIRM_DELETE + token_delete,
        content_type="application/json",
        headers=tests.DEFAULT_HEADER,
    )

    assert response.status_code == http.HTTPStatus.OK

    # list the project
    response = client.get(
        tests.DDSEndpoint.LIST_PROJ,
        headers=token_unitadmin,
        json={"usage": True},
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    public_project = response.json.get("project_info")[0]

    # check that the name is Former User
    assert "Former User" == public_project.get("Created by")
    


def test_list_proj_access_granted_ls(client):
    """Researcher should be able to list, "Created by" should be the Unit name"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
    response = client.get(tests.DDSEndpoint.LIST_PROJ, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    list_of_projects = response_json.get("project_info")
    assert "public_project_id" == list_of_projects[0].get("Project ID")
    # check that Researcher gets Unit name as "Created by"
    assert "Display Name" == list_of_projects[0].get("Created by")


def test_list_proj_unit_admin(client):
    """Unit admin should be able to list projects, "Created by" should be the creators name"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.get(
        tests.DDSEndpoint.LIST_PROJ,
        headers=token,
        json={"usage": True},
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    public_project = response.json.get("project_info")[0]
    assert "public_project_id" == public_project.get("Project ID")
    assert "Cost" in public_project.keys() and public_project["Cost"] is not None
    assert "Usage" in public_project.keys() and public_project["Usage"] is not None
    # check that Unit admin gets personal name as "Created by"
    assert "Unit User" == public_project.get("Created by")


def test_list_proj_unit_user(client):
    """Unit user should be able to list projects, "Created by" should be the creators name"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.get(
        tests.DDSEndpoint.LIST_PROJ,
        headers=token,
        json={"usage": True},
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    public_project = response.json.get("project_info")[0]
    assert "public_project_id" == public_project.get("Project ID")
    assert "Cost" in public_project.keys() and public_project["Cost"] is not None
    assert "Usage" in public_project.keys() and public_project["Usage"] is not None
    # check that Unit user gets personal name as "Created by"
    assert "Unit User" == public_project.get("Created by")


def test_list_proj_superadmin(client):
    """Super admin should be able to list projects, "Created by" should be the creators name"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client)
    response = client.get(
        tests.DDSEndpoint.LIST_PROJ,
        headers=token,
        json={"usage": True},
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    public_project = response.json.get("project_info")[0]
    assert "public_project_id" == public_project.get("Project ID")
    assert "Cost" in public_project.keys() and public_project["Cost"] is not None
    assert "Usage" in public_project.keys() and public_project["Usage"] is not None
    # check that Super admin gets personal name as "Created by"
    assert "Unit User" == public_project.get("Created by")


def test_list_only_active_projects_unit_user(client):
    """Unit admin should be able to list only active projects without --show-all flag"""

    # set one of the project as inactive
    inactive_project: models.Project = models.Project.query.first()
    inactive_project.is_active = False
    db.session.commit()

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.get(
        tests.DDSEndpoint.LIST_PROJ,
        headers=token,
        json={"usage": True},
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert len(response.json.get("project_info")) == 4


def test_list_all_projects_unit_user(client):
    """Unit admin should be able to list inactive projects with the --show-all flag"""

    # set one of the project as inactive
    inactive_project: models.Project = models.Project.query.first()
    inactive_project.is_active = False
    db.session.commit()

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.get(
        tests.DDSEndpoint.LIST_PROJ,
        headers=token,
        json={"usage": True, "show_all": True},
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert len(response.json.get("project_info")) == 5





def test_proj_private_successful(client):
    """Successfully get the private key"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.get(tests.DDSEndpoint.PROJ_PRIVATE, query_string=proj_query, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("private")


def test_proj_private_without_project(client):
    """Attempting to get the private key without specifying a project"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.get(tests.DDSEndpoint.PROJ_PRIVATE, headers=token)
    response_json = response.json
    assert "project" in response_json
    assert "Project ID required." in response_json["project"].get("message")


def test_proj_public_no_token(client):
    """Attempting to get the public key without a token should not work"""

    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        headers=tests.DEFAULT_HEADER,
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert "No token" in response_json.get("message")


def test_proj_public_insufficient_credentials(client):
    """If the project access has not been granted, the public key should not be provided."""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC, query_string=proj_query_restricted, headers=token
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    response_json = response.json
    assert "Project access denied" in response_json.get("message")


def test_list_researchusers_in_proj_by_researchuser(client):
    """Researchuser in project should be able to list researchusers"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
    response = client.get(tests.DDSEndpoint.LIST_PROJ_USERS, query_string=proj_query, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    response_list = response.json.get("research_users")
    assert response_list
    proj = models.Project.query.filter_by(public_id=proj_query["project"]).one_or_none()
    actual_user_list = []
    for user in proj.researchusers:
        info = {"User Name": "", "Primary email": "", "Role": ""}
        info["User Name"] = user.researchuser.username
        info["Role"] = "Owner" if user.owner else "Researcher"
        for user_email in user.researchuser.emails:
            if user_email.primary:
                info["Primary email"] = user_email.email
        actual_user_list.append(info)
    for invitee in proj.project_invite_keys:
        info = {"User Name": "", "Primary email": "", "Role": ""}
        role = "Owner" if invitee.owner else "Researcher"
        info["User Name"] = "NA (Pending)"
        info["Primary email"] = f"{invitee.invite.email} (Pending)"
        info["Role"] = f"{role} (Pending)"
        actual_user_list.append(info)

    case = unittest.TestCase()
    case.assertCountEqual(response_list, actual_user_list)


def test_list_researchusers_in_proj_by_unituser(client):
    """Unituser in project in unit should be able to list researchusers"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.get(tests.DDSEndpoint.LIST_PROJ_USERS, query_string=proj_query, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    response_list = response.json.get("research_users")
    assert response_list
    proj = models.Project.query.filter_by(public_id=proj_query["project"]).one_or_none()
    actual_user_list = []
    for user in proj.researchusers:
        info = {"User Name": "", "Primary email": "", "Role": ""}
        info["User Name"] = user.researchuser.username
        info["Role"] = "Owner" if user.owner else "Researcher"
        for user_email in user.researchuser.emails:
            if user_email.primary:
                info["Primary email"] = user_email.email
        actual_user_list.append(info)
    for invitee in proj.project_invite_keys:
        info = {"User Name": "", "Primary email": "", "Role": ""}
        role = "Owner" if invitee.owner else "Researcher"
        info["User Name"] = "NA (Pending)"
        info["Primary email"] = f"{invitee.invite.email} (Pending)"
        info["Role"] = f"{role} (Pending)"
        actual_user_list.append(info)

    case = unittest.TestCase()
    case.assertCountEqual(response_list, actual_user_list)


def test_list_researchusers_not_in_proj_by_researchuser(client):
    """Researchuser not in project should not be able to list researchusers"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser2"]).token(client)
    response = client.get(tests.DDSEndpoint.LIST_PROJ_USERS, query_string=proj_query, headers=token)
    assert response.status_code == http.HTTPStatus.FORBIDDEN
