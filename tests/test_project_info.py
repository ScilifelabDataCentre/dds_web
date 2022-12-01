# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import unittest

# Own
import tests


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
change_proj_title_json = {"project": "public_project_id", "title": "New Title"}

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
    response = client.put(tests.DDSEndpoint.PROJECT_INFO, headers=token)
    response_json = response.json
    assert "Required data missing from request!" in response_json.get("message")


# def test_change_proj_tiitle_only_unit_user(client):
#     """Unit admin should be able to change project title"""

#     token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
#     response = client.put(tests.DDSEndpoint.PROJECT_INFO, headers=token, json=change_proj_title_json)
#     # assert response.status_code == http.HTTPStatus.OK
#     response_json = response.json
#     assert "all good" == response_json.get("message")
