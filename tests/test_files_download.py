# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import json
import unittest

# Own
from dds_web.api import api_s3_connector
from dds_web.database import models
import tests


def get_json_file_info(client, args: dict, user_type="researchuser") -> dict:
    """Make a request for file info."""
    response = client.get(
        tests.DDSEndpoint.FILE_INFO,
        headers=tests.UserAuth(tests.USER_CREDENTIALS[user_type]).token(client),
        **args,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    return response.json


def test_file_download_empty(client):
    """Make empty request."""
    args = {}
    response_json = get_json_file_info(client, args)
    assert response_json
    assert "Required data missing from request" in response_json.get("message")


def test_file_download_no_project(client):
    """Make request with no project ID."""
    args = {"json": ["filename1"]}
    response_json = get_json_file_info(client, args)
    assert response_json
    assert (
        "project" in response_json
        and response_json["project"].get("message") == "Project ID required."
    )


def test_file_download_project_none(client):
    """Make request with project as None."""
    args = {
        "json": ["filename1"],
        "query_string": {"project": None},
    }
    response_json = get_json_file_info(client, args)
    assert response_json
    assert (
        "project" in response_json
        and response_json["project"].get("message") == "Project ID required."
    )


def test_file_download_unknown_field(client):
    """Make request with unknown field passed."""
    args = {
        "json": ["filename1"],
        "query_string": {"test": "test"},
    }
    response_json = get_json_file_info(client, args)
    assert response_json
    assert (
        "project" in response_json
        and response_json["project"].get("message") == "Project ID required."
    )


# ---


def get_json_file_info_all(client, args: dict, user_type="researchuser") -> dict:
    """Make a request for file info."""
    response = client.get(
        tests.DDSEndpoint.FILE_INFO_ALL,
        headers=tests.UserAuth(tests.USER_CREDENTIALS[user_type]).token(client),
        **args,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    return response.json


def test_file_download_empty_all(client):
    """Make empty request."""
    args = {}
    response_json = get_json_file_info_all(client, args)
    assert response_json
    assert (
        "project" in response_json
        and response_json["project"].get("message") == "Project ID required."
    )


def test_file_download_project_none_all(client):
    """Make request with project as None."""
    args = {"query_string": {"project": None}}
    response_json = get_json_file_info_all(client, args)
    assert response_json
    assert (
        "project" in response_json
        and response_json["project"].get("message") == "Project ID required."
    )


def test_file_download_unknown_field_all(client):
    """Make request with unknown field passed."""
    args = {"query_string": {"test": "test"}}
    response_json = get_json_file_info_all(client, args)
    assert response_json
    assert (
        "project" in response_json
        and response_json["project"].get("message") == "Project ID required."
    )


# ---


def test_files_download_in_progress(client, boto3_session):
    """Try to download from a project that is in Progress"""

    response = client.get(
        tests.DDSEndpoint.FILE_INFO,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": "public_project_id"},
        json=["filename1"],
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Current Project status limits file download." in response.json["message"]

    response = client.get(
        tests.DDSEndpoint.FILE_INFO_ALL,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Current Project status limits file download." in response.json["message"]


def test_file_download(client, boto3_session):
    """Check if correct file info is returned for download and db updated when downloaded"""
    # Set status to available
    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": "public_project_id"},
        json={"new_status": "Available"},
    )
    assert response.status_code == http.HTTPStatus.OK

    with unittest.mock.patch(
        "dds_web.api.api_s3_connector.ApiS3Connector.generate_get_url"
    ) as mock_url:
        mock_url.return_value = "url"
        response = client.get(
            tests.DDSEndpoint.FILE_INFO,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
            query_string={"project": "public_project_id"},
            json=["filename1"],
        )
        assert response.status_code == http.HTTPStatus.OK
        # filename1 in conftest
        expected_output = {
            "filename1": {
                "name_in_bucket": "name_in_bucket_1",
                "subpath": "filename1/subpath",
                "size_original": 15000,
                "size_stored": 10000,
                "compressed": True,
                "salt": "A" * 32,
                "public_key": "B" * 64,
                "checksum": "C" * 64,
                "url": "url",
            }
        }
        files = response.json["files"]
        assert "filename1" in files
        unittest.TestCase().assertDictEqual(expected_output, files)

        file_in_db = models.File.query.filter_by(name="filename1").first()
        assert file_in_db.time_latest_download is None
        response = client.put(
            tests.DDSEndpoint.FILE_UPDATE,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
            query_string={"project": "public_project_id"},
            json={"name": "filename1"},
        )
        assert response.status_code == http.HTTPStatus.OK
        assert "File info updated." in response.json["message"]
        assert file_in_db.time_latest_download is not None


def test_file_download_invalid_cases(client, boto3_session):
    """Test download with empty/invalid file name"""

    response = client.put(
        tests.DDSEndpoint.FILE_UPDATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": "public_project_id"},
        json={"name": ""},
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "No file name specified. Cannot update file." in response.json["message"]

    response = client.put(
        tests.DDSEndpoint.FILE_UPDATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": "public_project_id"},
        json={"name": "filename_1"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Specified file does not exist." in response.json["message"]


def test_files_find_all_for_download(client, boto3_session):
    """Check if correct file info for all files is returned for download"""
    # Set status to available
    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": "public_project_id"},
        json={"new_status": "Available"},
    )
    assert response.status_code == http.HTTPStatus.OK

    with unittest.mock.patch(
        "dds_web.api.api_s3_connector.ApiS3Connector.generate_get_url"
    ) as mock_url:
        mock_url.return_value = "url"
        response = client.get(
            tests.DDSEndpoint.FILE_INFO_ALL,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
            query_string={"project": "public_project_id"},
        )
        assert response.status_code == http.HTTPStatus.OK
        # filenames in conftest
        expected_output = {
            "filename1": {
                "subpath": "filename1/subpath",
                "size_original": 15000,
                "size_stored": 10000,
                "compressed": True,
                "salt": "A" * 32,
                "public_key": "B" * 64,
                "checksum": "C" * 64,
                "url": "url",
            },
            "filename2": {
                "subpath": "filename2/subpath",
                "size_original": 15000,
                "size_stored": 10000,
                "compressed": True,
                "salt": "D" * 32,
                "public_key": "E" * 64,
                "checksum": "F" * 64,
                "url": "url",
            },
        }
        for i in range(5):
            expected_output[f"filename_a{i+1}"] = {
                "subpath": f"sub/path/to/folder{i+1}",
                "size_original": 5000 * (i + 1),
                "size_stored": 3000 * (i + 1),
                "compressed": True,
                "salt": chr(ord("A") + 3 * i) * 32,
                "public_key": chr(ord("B") + 3 * i) * 64,
                "checksum": chr(ord("C") + 3 * i) * 64,
                "url": "url",
            }
            expected_output[f"filename_b{i+1}"] = {
                "subpath": f"sub/path/to/files",
                "size_original": 500 * (i + 1),
                "size_stored": 300 * (i + 1),
                "compressed": True,
                "salt": chr(ord("Z") - 3 * i) * 32,
                "public_key": chr(ord("Y") - 3 * i) * 64,
                "checksum": chr(ord("X") - 3 * i) * 64,
                "url": "url",
            }

        files = response.json["files"]
        for file in files:
            files[file].pop("name_in_bucket")

        assert "filename1" in files
        assert "filename2" in files
        for i in range(5):
            assert f"filename_a{i+1}" in files
            assert f"filename_b{i+1}" in files
        unittest.TestCase().assertDictEqual(expected_output, files)
