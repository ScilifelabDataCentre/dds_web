# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import datetime
import json
import pytest
import marshmallow
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

    response = client.get(tests.DDSEndpoint.LIST_PROJ)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" in response_json.get("message")


def test_list_proj_access_granted_ls(client):
    """Researcher should be able to list"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
    response = client.get(tests.DDSEndpoint.LIST_PROJ, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    list_of_projects = response_json.get("project_info")
    print(list_of_projects)
    assert "public_project_id" == list_of_projects[0].get("Project ID")


# public key


def test_proj_public_no_token(client):
    """Attempting to get the public key without a token should not work"""

    response = client.get(tests.DDSEndpoint.PROJ_PUBLIC)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert "Missing or incorrect credentials" in response_json.get("message")


def test_proj_public_no_project(client):
    """Attempting to get public key without a project should not work"""
    with pytest.raises(marshmallow.exceptions.ValidationError) as e_info:
        token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
        response = client.get(tests.DDSEndpoint.PROJ_PUBLIC, headers=token)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        response_json = response.json
        assert "without project ID" in response_json.get("message")


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
    proj = db.session.query(models.Project).filter_by(public_id=proj_query["project"]).one_or_none()
    actual_user_list = []
    for user in proj.researchusers:
        info = {"User Name": "", "Primary email": ""}
        info["User Name"] = user.researchuser.username
        for user_email in user.researchuser.emails:
            if user_email.primary:
                info["Primary email"] = user_email.email
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
    proj = db.session.query(models.Project).filter_by(public_id=proj_query["project"]).one_or_none()
    actual_user_list = []
    for user in proj.researchusers:
        info = {"User Name": "", "Primary email": ""}
        info["User Name"] = user.researchuser.username
        for user_email in user.researchuser.emails:
            if user_email.primary:
                info["Primary email"] = user_email.email
        actual_user_list.append(info)

    case = unittest.TestCase()
    case.assertCountEqual(response_list, actual_user_list)


def test_list_researchusers_not_in_proj_by_researchuser(client):
    """Researchuser in not project should not be able to list researchusers"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser2"]).token(client)
    response = client.get(tests.DDSEndpoint.LIST_PROJ_USERS, query_string=proj_query, headers=token)
    assert response.status_code == http.HTTPStatus.FORBIDDEN
