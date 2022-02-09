# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import json

# Own
from dds_web import db
from dds_web.database import models
import tests


# CONFIG ################################################################################## CONFIG #

proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}

# TESTS #################################################################################### TESTS #


def test_list_files_no_token(client):
    """Token required"""

    response = client.get(tests.DDSEndpoint.LIST_FILES)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "No token" in response_json.get("message")


def test_list_files_incorrect_project(client):
    """Researcher (current user) should specify a project that exists"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.get(
        tests.DDSEndpoint.LIST_FILES,
        headers=token,
        query_string={"project": "nonexisting_project_id"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json
    assert response_json.get("message")
    assert "The specified project does not exist." in response_json.get("message")
