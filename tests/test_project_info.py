# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import unittest

# Own
import tests
from dds_web.database import models


# CONFIG ################################################################################## CONFIG #

proj_info_items = [
    "Project ID",
    "Created by",
    "Status",
    "Last updated",
    "Size",
    "Title",
    "Description",
]
proj_query = {"project": "public_project_id"}
proj_query_restricted = {"project": "restricted_project_id"}

# TESTS #################################################################################### TESTS #

# Info listing
def test_list_proj_info_no_token(client):
    """Token required to list project information"""

    response = client.get(tests.DDSEndpoint.PROJECT_INFO, headers=tests.DEFAULT_HEADER)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "No token" in response_json.get("message")


def test_list_proj_info_without_project(client):
    """Attempting to get the project information without specifying a project"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.get(tests.DDSEndpoint.PROJECT_INFO, headers=token)
    response_json = response.json
    assert "Missing required information: 'project'" in response_json.get("message")


def test_list_proj_info_access_granted(client):
    """Researcher should be able to list project information"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
    response = client.get(tests.DDSEndpoint.PROJECT_INFO, headers=token, query_string=proj_query)
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    project_info = response_json.get("project_info")

    assert "public_project_id" == project_info.get("Project ID")
    # check that endpoint returns dictionary and not a list
    assert isinstance(project_info, dict)


def test_list_proj_info_unit_user(client):
    """Unit user should be able to list project information"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.get(tests.DDSEndpoint.PROJECT_INFO, headers=token, query_string=proj_query)
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    project_info = response_json.get("project_info")

    assert "public_project_id" == project_info.get("Project ID")
    assert (
        "This is a test project. You will be able to upload to but NOT download"
        in project_info.get("Description")
    )
    assert "Size" in project_info.keys() and project_info["Size"] is not None


def test_list_proj_info_returned_items(client):
    """Returned project information should contain certain items"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.get(tests.DDSEndpoint.PROJECT_INFO, headers=token, query_string=proj_query)
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    project_info = response_json.get("project_info")

    assert all(item in project_info for item in proj_info_items)


def test_list_project_info_by_researchuser_not_in_project(client):
    """Researchuser not in project should not be able to list project info"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser2"]).token(client)
    response = client.get(tests.DDSEndpoint.PROJECT_INFO, query_string=proj_query, headers=token)
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    response_json = response.json
    assert "Project access denied" in response_json.get("message")


def test_list_proj_info_public_insufficient_credentials(client):
    """If the project access has not been granted, the project info should not be provided."""

    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
    response = client.get(
        tests.DDSEndpoint.PROJECT_INFO, query_string=proj_query_restricted, headers=token
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    response_json = response.json
    assert "Project access denied" in response_json.get("message")


# Info changing
def test_change_proj_info_no_token(client):
    """Token required to change project information"""

    response = client.put(tests.DDSEndpoint.PROJECT_INFO, headers=tests.DEFAULT_HEADER)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "No token" in response_json.get("message")


def test_change_proj_info_without_project(client):
    """Attempting to change the project information without specifying a project"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.put(tests.DDSEndpoint.PROJECT_INFO, headers=token)
    response_json = response.json
    assert "Required data missing from request!" in response_json.get("message")


def test_change_proj_info_without_json(client):
    """Attempting to change the project information without specifying any option"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.put(tests.DDSEndpoint.PROJECT_INFO, headers=token, query_string=proj_query)
    response_json = response.json
    assert "Required data missing from request!" in response_json.get("message")


def test_change_proj_title_only_super_admin_forbidden(client):
    """Super admin should not be able to change project title"""

    project = models.Project.query.filter_by(public_id="public_project_id").first()
    assert "test project_title" == project.title

    token = tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_INFO,
        headers=token,
        query_string=proj_query,
        json={"title": "New title"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    response_json = response.json
    assert "Insufficient credentials" == response_json.get("message")
    assert "test project_title" == project.title


def test_change_proj_title_only_unit_user(client):
    """Unit user should be able to change project title"""

    project = models.Project.query.filter_by(public_id="public_project_id").first()
    assert "test project_title" == project.title

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_INFO,
        headers=token,
        query_string=proj_query,
        json={"title": "New title"},
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert "public_project_id info was successfully updated." == response_json.get("message")
    assert "New title" == project.title
    assert (
        "This is a test project. You will be able to upload to but NOT download from this project. Create a new project to test the entire system. "
        == project.description
    )
    assert "PI" == project.pi


def test_change_proj_title_only_disallowed_chars_unit_admin(client):
    """Disallowed characters in title should not pass validation"""

    project = models.Project.query.filter_by(public_id="public_project_id").first()
    assert "test project_title" == project.title

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_INFO,
        headers=token,
        query_string=proj_query,
        json={"title": "New <9f><98> title"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert "are not allowed." in response_json.get("message")
    assert "test project_title" == project.title


def test_change_proj_description_only_unit_admin(client):
    """
    Unit admin should be able to change project description.
    Title and PI shold remain the same.
    """

    project = models.Project.query.filter_by(public_id="public_project_id").first()
    assert (
        "This is a test project. You will be able to upload to but NOT download from this project. Create a new project to test the entire system. "
        == project.description
    )

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_INFO,
        headers=token,
        query_string=proj_query,
        json={"description": "New description"},
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert "public_project_id info was successfully updated." == response_json.get("message")
    assert "test project_title" == project.title
    assert "New description" == project.description
    assert "PI" == project.pi


def test_change_proj_description_only_unicode_emojis_unit_user(client):
    """Unit user should be able to change project description"""

    project = models.Project.query.filter_by(public_id="public_project_id").first()
    assert (
        "This is a test project. You will be able to upload to but NOT download from this project. Create a new project to test the entire system. "
        == project.description
    )

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_INFO,
        headers=token,
        query_string=proj_query,
        json={"description": "New description \U0001FA00-\U0001FA6F"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert "This input is not allowed:" in response_json.get("message")
    assert (
        "This is a test project. You will be able to upload to but NOT download from this project. Create a new project to test the entire system. "
        == project.description
    )


def test_change_proj_pi_only_valid_email_researcher(client):
    """
    Researcher should be able to change project PI.
    Title and description should remain the same.
    """

    project = models.Project.query.filter_by(public_id="public_project_id").first()
    assert "PI" == project.pi

    token = tests.UserAuth(tests.USER_CREDENTIALS["researcher"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_INFO,
        headers=token,
        query_string=proj_query,
        json={"pi": "pi@email.new"},
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert "public_project_id info was successfully updated." == response_json.get("message")
    assert "test project_title" == project.title
    assert (
        "This is a test project. You will be able to upload to but NOT download from this project. Create a new project to test the entire system. "
        == project.description
    )
    assert "pi@email.new" == project.pi


def test_change_proj_pi_only_invalid_email_unit_admin(client):
    """Unit admin should be able to change project PI"""

    project = models.Project.query.filter_by(public_id="public_project_id").first()
    assert "PI" == project.pi

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_INFO,
        headers=token,
        query_string=proj_query,
        json={"pi": "New PI"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert "The PI email is invalid" == response_json.get("message")
    assert "PI" == project.pi


def test_change_proj_title_and_pi_projectowner(client):
    """
    Project Owner should be able to change title and PI of a project.
    Description should remain unchanged.
    """

    project = models.Project.query.filter_by(public_id="public_project_id").first()
    assert "test project_title" == project.title
    assert "PI" == project.pi

    token = tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_INFO,
        headers=token,
        query_string=proj_query,
        json={
            "title": "New title",
            "pi": "pi@email.new",
        },
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert "public_project_id info was successfully updated." == response_json.get("message")
    assert "New title" == project.title
    assert (
        "This is a test project. You will be able to upload to but NOT download from this project. Create a new project to test the entire system. "
        == project.description
    )
    assert "pi@email.new" == project.pi


def test_change_proj_all_items_projectowner(client):
    """Project Owner should be able to change all three project info items"""

    project = models.Project.query.filter_by(public_id="public_project_id").first()
    assert "test project_title" == project.title
    assert (
        "This is a test project. You will be able to upload to but NOT download from this project. Create a new project to test the entire system. "
        == project.description
    )
    assert "PI" == project.pi

    token = tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_INFO,
        headers=token,
        query_string=proj_query,
        json={
            "title": "New title",
            "description": "New description",
            "pi": "pi@email.new",
        },
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert "public_project_id info was successfully updated." == response_json.get("message")
    assert "New title" == project.title
    assert "New description" == project.description
    assert "pi@email.new" == project.pi
