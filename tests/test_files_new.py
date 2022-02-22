import http
import json
import time

import pytest
import marshmallow

from dds_web import db
import dds_web.utils
from dds_web.database import models
import tests

first_new_file = {
    "name": "filename1",
    "name_in_bucket": "filebucketname1",
    "subpath": "subpath",
    "size": 1000,
    "size_processed": 500,
    "compressed": True,
    "public_key": "p" * 64,
    "salt": "s" * 32,
    "checksum": "c" * 64,
}

# TOOLS #################################################################################### TOOLS #


def file_in_db(test_dict, project):
    """Checks if the file is in the db."""

    if models.File.query.filter_by(
        name=test_dict["name"],
        name_in_bucket=test_dict["name_in_bucket"],
        subpath=test_dict["subpath"],
        size_original=test_dict["size"],
        size_stored=test_dict["size_processed"],
        compressed=test_dict["compressed"],
        public_key=test_dict["public_key"],
        salt=test_dict["salt"],
        checksum=test_dict["checksum"],
        project_id=project,
    ).one_or_none():
        return True

    return False


def project_row(project_id):
    """Get project row from database."""

    return models.Project.query.filter_by(public_id=project_id).one_or_none()


# TESTS #################################################################################### TESTS #


def test_new_file_empty(client):
    """Make empty request."""
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
    )
    response_json = response.json
    assert response_json
    assert "Required data missing from request" in response_json.get("message")


def test_new_file_no_project(client):
    """Make request with no project ID."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "project" in response_json
        and response_json["project"].get("message") == "Project ID required."
    )


def test_new_file_project_none(client):
    """Make request with project as None."""
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": None},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "project" in response_json
        and response_json["project"].get("message") == "Project ID required."
    )


def test_new_file_unknown_field(client):
    """Make request with unknown field passed."""
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"test": "project_id"},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "project" in response_json
        and response_json["project"].get("message") == "Project ID required."
    )


def test_new_file_missing_name(client):
    """Make request with missing file name."""
    file_no_name = first_new_file.copy()
    file_no_name.pop("name")

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_name),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert "name" in response_json and response_json["name"].get("message") == "File name required."


def test_new_file_name_none(client):
    """Make request with missing file name."""
    file_no_name = first_new_file.copy()
    file_no_name["name"] = None

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_name),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert "name" in response_json and response_json["name"].get("message") == "File name required."


def test_new_file_missing_nameinbucket(client):
    """Make request with missing file name in bucket."""
    file_no_nameinbucket = first_new_file.copy()
    file_no_nameinbucket.pop("name_in_bucket")

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_nameinbucket),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "name_in_bucket" in response_json
        and response_json["name_in_bucket"].get("message") == "Remote file name required."
    )


def test_new_file_nameinbucket_none(client):
    """Make request with missing file name in bucket."""
    file_no_nameinbucket = first_new_file.copy()
    file_no_nameinbucket["name_in_bucket"] = None

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_nameinbucket),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "name_in_bucket" in response_json
        and response_json["name_in_bucket"].get("message") == "Remote file name required."
    )


def test_new_file_missing_subpath(client):
    """Make request with missing file subpath."""
    file_no_subpath = first_new_file.copy()
    file_no_subpath.pop("subpath")

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_subpath),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "subpath" in response_json
        and response_json["subpath"].get("message") == "Subpath required."
    )


def test_new_file_subpath_none(client):
    """Make request with missing file subpath."""
    file_no_subpath = first_new_file.copy()
    file_no_subpath["subpath"] = None

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_subpath),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "subpath" in response_json
        and response_json["subpath"].get("message") == "Subpath required."
    )


def test_new_file_missing_size(client):
    """Make request with missing file size."""
    file_no_size = first_new_file.copy()
    file_no_size.pop("size")

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_size),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert "size" in response_json and response_json["size"].get("message") == "File size required."


def test_new_file_size_none(client):
    """Make request with missing file size."""
    file_no_size = first_new_file.copy()
    file_no_size["size"] = None

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_size),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert "size" in response_json and response_json["size"].get("message") == "File size required."


def test_new_file_missing_size_processed(client):
    """Make request with missing file size_processed."""
    file_no_size_processed = first_new_file.copy()
    file_no_size_processed.pop("size_processed")

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_size_processed),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "size_processed" in response_json
        and response_json["size_processed"].get("message") == "File processed size required."
    )


def test_new_file_size_processed_none(client):
    """Make request with missing file size."""
    file_no_size_processed = first_new_file.copy()
    file_no_size_processed["size_processed"] = None

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_size_processed),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "size_processed" in response_json
        and response_json["size_processed"].get("message") == "File processed size required."
    )


def test_new_file_missing_compressed(client):
    """Make request with missing file compressed."""
    file_no_compressed = first_new_file.copy()
    file_no_compressed.pop("compressed")

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_compressed),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "compressed" in response_json
        and response_json["compressed"].get("message")
        == "Boolean compression information required."
    )


def test_new_file_compressed_none(client):
    """Make request with missing file compressed."""
    file_no_compressed = first_new_file.copy()
    file_no_compressed["compressed"] = None

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_compressed),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "compressed" in response_json
        and response_json["compressed"].get("message")
        == "Boolean compression information required."
    )


def test_new_file_missing_public_key(client):
    """Make request with missing file public_key."""
    file_no_public_key = first_new_file.copy()
    file_no_public_key.pop("public_key")

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_public_key),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "public_key" in response_json
        and response_json["public_key"].get("message") == "Public key for file required."
    )


def test_new_file_public_key_none(client):
    """Make request with missing file public_key."""
    file_no_public_key = first_new_file.copy()
    file_no_public_key["public_key"] = None

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_public_key),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "public_key" in response_json
        and response_json["public_key"].get("message") == "Public key for file required."
    )


def test_new_file_missing_salt(client):
    """Make request with missing file salt."""
    file_no_salt = first_new_file.copy()
    file_no_salt.pop("salt")

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_salt),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert "salt" in response_json and response_json["salt"].get("message") == "File salt required."


def test_new_file_salt_none(client):
    """Make request with missing file salt."""
    file_no_salt = first_new_file.copy()
    file_no_salt["salt"] = None

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_salt),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert "salt" in response_json and response_json["salt"].get("message") == "File salt required."


def test_new_file_missing_checksum(client):
    """Make request with missing file checksum."""
    file_no_checksum = first_new_file.copy()
    file_no_checksum.pop("checksum")

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_checksum),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "checksum" in response_json
        and response_json["checksum"].get("message") == "Checksum required."
    )


def test_new_file_checksum_none(client):
    """Make request with missing file checksum."""
    file_no_checksum = first_new_file.copy()
    file_no_checksum["checksum"] = None

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_checksum),
        content_type="application/json",
    )
    response_json = response.json
    assert response_json
    assert (
        "checksum" in response_json
        and response_json["checksum"].get("message") == "Checksum required."
    )


def test_new_file(client):
    """Add and overwrite file to database."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    assert file_in_db(test_dict=first_new_file, project=project_1.id)

    # Update file with incomplete info
    updated_file = first_new_file.copy()
    updated_file.pop("size")
    response = client.put(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(updated_file),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Information is missing, cannot add file to database." in response.json["message"]

    # Update with full info
    updated_file["size"] = 1200
    updated_file["size_processed"] = 600

    response = client.put(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(updated_file),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    assert file_in_db(test_dict=updated_file, project=project_1.id)
    assert f"File '{updated_file['name']}' updated in db." in response.json["message"]


def test_update_nonexistent_file(client):
    """Try to update a non existent file"""
    response = client.put(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert (
        f"Cannot update non-existent file '{first_new_file['name']}' in the database!"
        in response.json["message"]
    )


def test_match_file_endpoint(client):
    """Test Match file endpoint"""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1
    assert project_1.current_status == "In Progress"

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert file_in_db(test_dict=first_new_file, project=project_1.id)

    # Match existing file
    response = client.get(
        tests.DDSEndpoint.FILE_MATCH,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps([first_new_file["name"]]),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json["files"][first_new_file["name"]] == first_new_file["name_in_bucket"]

    # Match nonexistent file
    response = client.get(
        tests.DDSEndpoint.FILE_MATCH,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(["non_existent_file"]),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json["files"] is None


def test_upload_and_delete_file(client, boto3_session):
    """Upload and delete a file"""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1
    assert project_1.current_status == "In Progress"

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert file_in_db(test_dict=first_new_file, project=project_1.id)

    response = client.delete(
        tests.DDSEndpoint.REMOVE_FILE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps([first_new_file["name"]]),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert not response.json["not_removed"]
    assert not file_in_db(test_dict=first_new_file, project=project_1.id)


def test_upload_and_delete_folder(client, boto3_session):
    """Upload and delete a folder"""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1
    assert project_1.current_status == "In Progress"

    file_1_in_folder = first_new_file.copy()
    file_1_in_folder["name"] = "file_1_in_folder"
    file_1_in_folder["name_in_bucket"] = "bucketfile_1_in_folder"
    file_2_in_folder = first_new_file.copy()
    file_2_in_folder["name"] = "file_2_in_folder"
    file_2_in_folder["name_in_bucket"] = "bucketfile_2_in_folder"

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_1_in_folder),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert file_in_db(test_dict=file_1_in_folder, project=project_1.id)
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_2_in_folder),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert file_in_db(test_dict=file_2_in_folder, project=project_1.id)

    # Remove invalid folder
    response = client.delete(
        tests.DDSEndpoint.REMOVE_FOLDER,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(["invalid_folder"]),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json["not_exists"][0] == "invalid_folder"

    # Remove valid folder
    response = client.delete(
        tests.DDSEndpoint.REMOVE_FOLDER,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps([file_1_in_folder["subpath"]]),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert not response.json["not_removed"]
    assert not file_in_db(test_dict=file_1_in_folder, project=project_1.id)
    assert not file_in_db(test_dict=file_2_in_folder, project=project_1.id)


def test_upload_move_available_delete_file(client, boto3_session):
    """Test delete a file once project has been made available"""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1
    assert project_1.current_status == "In Progress"
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert file_in_db(test_dict=first_new_file, project=project_1.id)

    # Make project Available
    new_status = {"new_status": "Available"}
    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(new_status),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert project_1.current_status == "Available"
    # Try deleting the uploaded file
    response = client.delete(
        tests.DDSEndpoint.REMOVE_FILE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps([first_new_file["name"]]),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Project Status prevents files from being deleted." in response.json["message"]

    # Move project back to In Progress
    time.sleep(1)
    new_status["new_status"] = "In Progress"
    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(new_status),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert project_1.current_status == "In Progress"

    # Try deleting uploaded file again
    response = client.delete(
        tests.DDSEndpoint.REMOVE_FILE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps([first_new_file["name"]]),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert (
        "Existing project contents cannot be deleted since the project has been previously made available to recipients."
        in response.json["message"]
    )


def test_upload_and_remove_all_project_contents(client, boto3_session):
    """Upload and then delete all project contents"""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1
    assert project_1.current_status == "In Progress"

    # Try to remove all contents on empty project
    response = client.delete(
        tests.DDSEndpoint.REMOVE_PROJ_CONT,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "There are no project contents to delete." in response.json["message"]

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert file_in_db(test_dict=first_new_file, project=project_1.id)

    project_1 = project_row(project_id="file_testing_project")
    assert project_1
    assert project_1.current_status == "In Progress"

    file_1_in_folder = first_new_file.copy()
    file_1_in_folder["name"] = "file_1_in_folder"
    file_1_in_folder["name_in_bucket"] = "bucketfile_1_in_folder"

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_1_in_folder),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert file_in_db(test_dict=file_1_in_folder, project=project_1.id)

    # Remove all contents
    response = client.delete(
        tests.DDSEndpoint.REMOVE_PROJ_CONT,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json["removed"]
    assert not file_in_db(test_dict=first_new_file, project=project_1.id)
    assert not file_in_db(test_dict=file_1_in_folder, project=project_1.id)


def test_new_file_invalid_credentials(client):
    """Test create file with researcher creds."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researcher"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    assert not file_in_db(test_dict=first_new_file, project=project_1.id)


def test_new_file_name_too_short(client):
    """Test adding a file with no name."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_no_name = first_new_file.copy()
    file_no_name["name"] = ""
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_name),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert not file_in_db(test_dict=file_no_name, project=project_1.id)


def test_new_file_nameinbucket_too_short(client):
    """Test adding a file with no name_in_bucket."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_no_nameinbucket = first_new_file.copy()
    file_no_nameinbucket["name_in_bucket"] = ""
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_nameinbucket),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert not file_in_db(test_dict=file_no_nameinbucket, project=project_1.id)


def test_new_file_subpath_too_short(client):
    """Add file without subpath."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_no_subpath = first_new_file.copy()
    file_no_subpath["subpath"] = ""
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_no_subpath),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert not file_in_db(test_dict=file_no_subpath, project=project_1.id)


def test_new_file_size_bigint(client):
    """Add huge file."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_size_bigint = first_new_file.copy()
    file_size_bigint["size"] = 9223372036854775807  # 9223 petabytes (big int sql definition)
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_size_bigint),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert file_in_db(test_dict=file_size_bigint, project=project_1.id)


def test_new_file_sizeprocessed_bigint(client):
    """Add huge file."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_sizeprocessed_bigint = first_new_file.copy()
    file_sizeprocessed_bigint[
        "size_processed"
    ] = 9223372036854775807  # 9223 petabytes (big int sql definition)
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_sizeprocessed_bigint),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert file_in_db(test_dict=file_sizeprocessed_bigint, project=project_1.id)


def test_new_file_publickey_wrong_length(client):
    """Test adding a file with an incorrect public key length."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_wrong_public_key = first_new_file.copy()
    file_wrong_public_key["public_key"] = "test"
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_wrong_public_key),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert not file_in_db(test_dict=file_wrong_public_key, project=project_1.id)


def test_new_file_salt_wrong_length(client):

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_wrong_salt = first_new_file.copy()
    file_wrong_salt["salt"] = "test"
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_wrong_salt),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert not file_in_db(test_dict=file_wrong_salt, project=project_1.id)


def test_new_file_checksum_wrong_length(client):

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_wrong_checksum = first_new_file.copy()
    file_wrong_checksum["checksum"] = "test"
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(file_wrong_checksum),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert not file_in_db(test_dict=file_wrong_checksum, project=project_1.id)


def test_new_file_wrong_status(client):
    project_1 = project_row(project_id="file_testing_project")
    new_status = {"new_status": "Available"}
    assert project_1

    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK

    assert project_1.current_status == "Available"

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": "file_testing_project"},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Project not in right status to upload/modify files" in response.json.get("message")
