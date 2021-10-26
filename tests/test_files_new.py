import json
from dds_web import db
import dds_web.utils
from dds_web.database import models
import tests
import pytest
import http
import marshmallow

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

    if (
        db.session.query(models.File)
        .filter_by(
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
        )
        .one_or_none()
    ):
        return True

    return False


def project_row(project_id):
    """Get project row from database."""

    return db.session.query(models.Project).filter_by(public_id=project_id).one_or_none()


# TESTS #################################################################################### TESTS #


def test_new_file(client):
    """Add file to database."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
        query_string={"project": "file_testing_project"},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    assert file_in_db(test_dict=first_new_file, project=project_1.id)


def test_new_file_invalid_credentials(client):
    """Test create file with researcher creds."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researcher"]).post_headers(),
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
    with pytest.raises(marshmallow.ValidationError):
        response = client.post(
            tests.DDSEndpoint.FILE_NEW,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
            query_string={"project": "file_testing_project"},
            data=json.dumps(file_no_name),
            content_type="application/json",
        )

    assert not file_in_db(test_dict=file_no_name, project=project_1.id)


def test_new_file_nameinbucket_too_short(client):
    """Test adding a file with no name_in_bucket."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_no_nameinbucket = first_new_file.copy()
    file_no_nameinbucket["name_in_bucket"] = ""
    with pytest.raises(marshmallow.ValidationError):
        response = client.post(
            tests.DDSEndpoint.FILE_NEW,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
            query_string={"project": "file_testing_project"},
            data=json.dumps(file_no_nameinbucket),
            content_type="application/json",
        )

    assert not file_in_db(test_dict=file_no_nameinbucket, project=project_1.id)


def test_new_file_subpath_too_short(client):
    """Add file without subpath."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_no_subpath = first_new_file.copy()
    file_no_subpath["subpath"] = ""
    with pytest.raises(marshmallow.ValidationError):
        response = client.post(
            tests.DDSEndpoint.FILE_NEW,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
            query_string={"project": "file_testing_project"},
            data=json.dumps(file_no_subpath),
            content_type="application/json",
        )

    assert not file_in_db(test_dict=file_no_subpath, project=project_1.id)


def test_new_file_size_bigint(client):
    """Add huge file."""

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_size_bigint = first_new_file.copy()
    file_size_bigint["size"] = 9223372036854775807  # 9223 petabytes (big int sql definition)
    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
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
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
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
    file_wrong_public_key["public_key"] = "test"  # 9223 petabytes (big int sql definition)
    with pytest.raises(marshmallow.ValidationError):
        response = client.post(
            tests.DDSEndpoint.FILE_NEW,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
            query_string={"project": "file_testing_project"},
            data=json.dumps(file_wrong_public_key),
            content_type="application/json",
        )
    assert not file_in_db(test_dict=file_wrong_public_key, project=project_1.id)


def test_new_file_salt_wrong_length(client):

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_wrong_salt = first_new_file.copy()
    file_wrong_salt["salt"] = "test"  # 9223 petabytes (big int sql definition)
    with pytest.raises(marshmallow.ValidationError):
        response = client.post(
            tests.DDSEndpoint.FILE_NEW,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
            query_string={"project": "file_testing_project"},
            data=json.dumps(file_wrong_salt),
            content_type="application/json",
        )
    assert not file_in_db(test_dict=file_wrong_salt, project=project_1.id)


def test_new_file_checksum_wrong_length(client):

    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    file_wrong_checksum = first_new_file.copy()
    file_wrong_checksum["checksum"] = "test"  # 9223 petabytes (big int sql definition)
    with pytest.raises(marshmallow.ValidationError):
        response = client.post(
            tests.DDSEndpoint.FILE_NEW,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
            query_string={"project": "file_testing_project"},
            data=json.dumps(file_wrong_checksum),
            content_type="application/json",
        )
    assert not file_in_db(test_dict=file_wrong_checksum, project=project_1.id)
