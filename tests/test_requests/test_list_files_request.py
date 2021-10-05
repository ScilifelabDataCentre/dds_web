# IMPORTS ################################################################################ IMPORTS #
# Standard library

# Installed
import http

# Own modules
import tests as dds_cli
from tests import user

# TESTS #################################################################################### TESTS #


def test_list_files_no_token(client):
    """Token required"""

    response = client.get(dds_cli.DDSEndpoint.LIST_FILES)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json()
    assert response_json.get("message")
    assert "Missing or incorrect credentials" in response_json.get("message")


def test_list_files_incorrect_project(client):
    """Researcher (current user) should specify a project that exists"""

    token = user.User(username="username", password="password").token
    response = client.get(
        dds_cli.DDSEndpoint.LIST_FILES, headers=token, params={"project": "private_project_id"}
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json()
    assert response_json.get("message")
    assert "The specified project does not exist." in response_json.get("message")


def test_list_files_correct_project(client):
    """Researcher (current user) should get the list of files"""

    token = user.User(username="username", password="password").token
    response = client.get(
        dds_cli.DDSEndpoint.LIST_FILES, headers=token, params={"project": "public_project_id"}
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json()
    files_folders = response_json.get("files_folders")
    assert "notafile.txt" == files_folders[0].get("name")
