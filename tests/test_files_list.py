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


def test_list_files_auth_not_available(client):
    """Verify that researchuser cannot list project contents if the project is In Progress."""
    response = client.get(
        tests.DDSEndpoint.LIST_FILES,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "no data available" in response.json["message"]


def test_list_files_auth(client):
    """Confirm that the correct files/folders are listed."""
    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": "public_project_id"},
        json={"new_status": "Available"},
    )
    assert response.status_code == http.HTTPStatus.OK

    response = client.get(
        tests.DDSEndpoint.LIST_FILES,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": "public_project_id"},
        json={"show_size": True},
    )
    expected = {
        "files_folders": [
            {"folder": True, "name": "filename1", "size": "15 KB"},
            {"folder": True, "name": "filename2", "size": "82.5 KB"},
            {"folder": True, "name": "sub", "size": "15 KB"},
        ]
    }
    assert "files_folders" in response.json
    assert len(response.json["files_folders"]) == len(expected["files_folders"])
    for entry in response.json["files_folders"]:
        assert len(entry) == 3
        assert entry["folder"] is True
    assert set(entry["name"] for entry in response.json["files_folders"]) == set(
        entry["name"] for entry in expected["files_folders"]
    )

    response = client.get(
        tests.DDSEndpoint.LIST_FILES,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": "public_project_id"},
        json={"subpath": ""},
    )
    expected = {
        "files_folders": [
            {"folder": True, "name": "filename1"},
            {"folder": True, "name": "filename2"},
            {"folder": True, "name": "sub"},
        ]
    }
    assert "files_folders" in response.json
    assert len(response.json["files_folders"]) == len(expected["files_folders"])
    for entry in response.json["files_folders"]:
        assert len(entry) == 2
        assert entry["folder"] is True
    assert set(entry["name"] for entry in response.json["files_folders"]) == set(
        entry["name"] for entry in expected["files_folders"]
    )

    response = client.get(
        tests.DDSEndpoint.LIST_FILES,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": "public_project_id"},
        json={"subpath": "sub/path"},
    )
    assert response.json == {"files_folders": [{"folder": True, "name": "to"}]}

    response = client.get(
        tests.DDSEndpoint.LIST_FILES,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": "public_project_id"},
        json={"subpath": "sub/path/to"},
    )
    # compare in multiple steps as the order of the returned entries is not guaranteed
    expected = {
        "files_folders": [
            {"folder": True, "name": "folder1"},
            {"folder": True, "name": "folder2"},
            {"folder": True, "name": "folder3"},
            {"folder": True, "name": "folder4"},
            {"folder": True, "name": "folder5"},
            {"folder": True, "name": "files"},
        ]
    }
    assert "files_folders" in response.json
    assert len(response.json["files_folders"]) == len(expected["files_folders"])
    for entry in response.json["files_folders"]:
        assert len(entry) == 2
        assert entry["folder"] is True
    assert set(entry["name"] for entry in response.json["files_folders"]) == set(
        entry["name"] for entry in expected["files_folders"]
    )

    response = client.get(
        tests.DDSEndpoint.LIST_FILES,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": "public_project_id"},
        json={"subpath": "sub/path/to/folder1"},
    )
    assert response.json == {"files_folders": [{"folder": False, "name": "filename_a1"}]}

    response = client.get(
        tests.DDSEndpoint.LIST_FILES,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": "public_project_id"},
        json={"subpath": "sub/path/to/files"},
    )
    # compare in multiple steps as the order of the returned entries is not guaranteed
    expected = {
        "files_folders": [
            {"folder": False, "name": "filename_b1"},
            {"folder": False, "name": "filename_b2"},
            {"folder": False, "name": "filename_b3"},
            {"folder": False, "name": "filename_b4"},
            {"folder": False, "name": "filename_b5"},
        ]
    }
    assert "files_folders" in response.json
    assert len(response.json["files_folders"]) == len(expected["files_folders"])
    for entry in response.json["files_folders"]:
        assert len(entry) == 2
        assert entry["folder"] is False
    assert set(entry["name"] for entry in response.json["files_folders"]) == set(
        entry["name"] for entry in expected["files_folders"]
    )


def test_list_project_with_no_files(client):
    """List project with no files"""

    response = client.get(
        tests.DDSEndpoint.LIST_FILES,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": "file_testing_project"},
    )
    assert response.status_code == http.HTTPStatus.OK
    assert "The project file_testing_project is empty." in response.json["message"]
    assert response.json["num_items"] == 0
