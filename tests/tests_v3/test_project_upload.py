# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import datetime

# Installed
import freezegun

# Own
from dds_web import db
import tests.tests_v3 as tests
from tests.tests_v3.test_files_new import project_row


# TESTS #################################################################################### TESTS #

# ProjectUploadComplete - "/proj/upload/complete"


def test_proj_upload_complete_updates_timestamp(client):
    """POST /proj/upload/complete refreshes date_updated and last_updated_by."""
    project_1 = project_row(project_id="file_testing_project")
    assert project_1

    frozen_before = datetime.datetime(2000, 1, 1, 12, 0, 0)
    frozen_after = datetime.datetime(2000, 1, 2, 12, 0, 0)

    with freezegun.freeze_time(frozen_before):
        project_1.date_updated = frozen_before
        db.session.commit()

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)

    with freezegun.freeze_time(frozen_after):
        response = client.post(
            tests.DDSEndpoint.PROJ_UPLOAD_COMPLETE,
            headers=token,
            query_string={"project": "file_testing_project"},
        )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json.get("message") == "Project upload timestamp updated."

    db.session.refresh(project_1)
    assert project_1.date_updated == frozen_after
    assert project_1.last_updated_by == "unitadmin"


def test_proj_upload_complete_unit_personnel_allowed(client):
    """Unit Personnel (non-admin unit user) can call POST /proj/upload/complete."""
    response = client.post(
        tests.DDSEndpoint.PROJ_UPLOAD_COMPLETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": "file_testing_project"},
    )
    assert response.status_code == http.HTTPStatus.OK


def test_proj_upload_complete_unauthorized_roles_denied(client):
    """Researcher and Project Owner cannot call POST /proj/upload/complete."""
    for role in ("researcher", "projectowner"):
        response = client.post(
            tests.DDSEndpoint.PROJ_UPLOAD_COMPLETE,
            headers=tests.UserAuth(tests.USER_CREDENTIALS[role]).token(client),
            query_string={"project": "file_testing_project"},
        )
        assert (
            response.status_code == http.HTTPStatus.FORBIDDEN
        ), f"Expected 403 for role '{role}', got {response.status_code}"


def test_proj_upload_complete_no_update_if_available(client, boto3_session):
    """POST /proj/upload/complete returns 400 when project status is Available."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)

    # Move project to Available
    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=token,
        query_string={"project": "file_testing_project"},
        json={"new_status": "Available"},
    )
    assert response.status_code == http.HTTPStatus.OK

    response = client.post(
        tests.DDSEndpoint.PROJ_UPLOAD_COMPLETE,
        headers=token,
        query_string={"project": "file_testing_project"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST


def test_proj_upload_complete_no_update_if_expired(client, boto3_session, mock_queue_redis):
    """POST /proj/upload/complete returns 400 when project status is Expired."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)

    # Move project to Available then Expired
    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=token,
        query_string={"project": "file_testing_project"},
        json={"new_status": "Available"},
    )
    assert response.status_code == http.HTTPStatus.OK

    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=token,
        query_string={"project": "file_testing_project"},
        json={"new_status": "Expired"},
    )
    assert response.status_code == http.HTTPStatus.OK

    response = client.post(
        tests.DDSEndpoint.PROJ_UPLOAD_COMPLETE,
        headers=token,
        query_string={"project": "file_testing_project"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
