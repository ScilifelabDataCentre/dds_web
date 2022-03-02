# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import json
import pytest
import marshmallow
import unittest

# Own
from dds_web.database import models
import tests


# CONFIG ################################################################################## CONFIG #

proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}
proj_query = {"project": "public_project_id"}
proj_query_restricted = {"project": "restricted_project_id"}

# TESTS #################################################################################### TESTS #


def test_list_proj_no_token(client):
    """Token required to list projects"""

    response = client.get(tests.DDSEndpoint.LIST_PROJ)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "No token" in response_json.get("message")


def test_list_proj_access_granted_ls(client):
    """Researcher should be able to list"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
    response = client.get(tests.DDSEndpoint.LIST_PROJ, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    list_of_projects = response_json.get("project_info")
    assert "public_project_id" == list_of_projects[0].get("Project ID")


def test_list_proj_unit_user(client):
    """Unit user should be able to list projects"""

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

    response = client.get(tests.DDSEndpoint.PROJ_PUBLIC)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert "No token" in response_json.get("message")


def test_proj_public_no_project(client):
    """Attempting to get public key without a project should not work"""
    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
    response = client.get(tests.DDSEndpoint.PROJ_PUBLIC, headers=token)
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert "project" in response_json
    assert "Project ID required." in response_json["project"].get("message")


def test_proj_public_insufficient_credentials(client):
    """If the project access has not been granted, the public key should not be provided."""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC, query_string=proj_query_restricted, headers=token
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    response_json = response.json
    assert "Project access denied" in response_json.get("message")


def test_project_public_researcher_get(client):
    """User should get access to public key"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
    response = client.get(tests.DDSEndpoint.PROJ_PUBLIC, query_string=proj_query, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("public")


def test_project_public_facility_put(client):
    """User should get access to public key"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.get(tests.DDSEndpoint.PROJ_PUBLIC, query_string=proj_query, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("public")


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
