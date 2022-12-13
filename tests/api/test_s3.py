import flask
import http
import sqlalchemy
import typing
from unittest.mock import patch

from tests import DDSEndpoint, DEFAULT_HEADER, UserAuth, USER_CREDENTIALS
from tests.api.test_project import mock_sqlalchemyerror
from dds_web.database import models
from dds_web import db


def mock_get_s3_info_none(_):
    return None, None, None, None


def test_get_s3_info_unauthorized(client: flask.testing.FlaskClient) -> None:
    """Only Unit Admin and Unit Personnel can get this info."""
    # Get project
    project: models.Project = models.Project.query.first()

    # Get users with access to project
    unit_users = db.session.query(models.UnitUser).filter(
        models.UnitUser.unit_id == project.unit_id
    )

    # Get users with no access to project
    unit_users_no_access = db.session.query(models.UnitUser).filter(
        models.UnitUser.unit_id != project.unit_id
    )

    # Returned info - expected
    expected_return: typing.Dict = {
        "safespring_project": project.responsible_unit.safespring_name,
        "url": project.responsible_unit.safespring_endpoint,
        "keys": {
            "access_key": project.responsible_unit.safespring_access,
            "secret_key": project.responsible_unit.safespring_secret,
        },
        "bucket": project.bucket,
    }

    # Try s3info - "/s3/proj"
    # Super Admin --> No
    super_admin_token = UserAuth(USER_CREDENTIALS["superadmin"]).token(client)
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=super_admin_token,
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # Unit Admin, correct unit --> Yes
    unit_admin: models.UnitUser = unit_users.filter(models.UnitUser.is_admin == True).first()
    unit_admin_token = UserAuth(USER_CREDENTIALS[unit_admin.username]).token(client)
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=unit_admin_token,
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    for x, y in expected_return.items():
        assert x in response_json
        assert response_json[x] == y

    # Unit Admin, incorrect unit --> No
    unit_admin_no_access: models.UnitUser = unit_users_no_access.filter(
        models.UnitUser.is_admin == True
    ).first()
    unit_admin_no_access_token = UserAuth(USER_CREDENTIALS[unit_admin_no_access.username]).token(
        client
    )
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=unit_admin_no_access_token,
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # Unit Personnel, correct unit --> Yes
    unit_personnel: models.UnitUser = unit_users.filter(models.UnitUser.is_admin == False).first()
    unit_personnel_token = UserAuth(USER_CREDENTIALS[unit_personnel.username]).token(client)
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=unit_personnel_token,
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    for x, y in expected_return.items():
        assert x in response_json
        assert response_json[x] == y

    # Unit Personnel, incorrect unit --> No
    unit_personnel_no_access: models.UnitUser = unit_users_no_access.filter(
        models.UnitUser.is_admin == False
    ).first()
    unit_personnel_no_access_token = UserAuth(
        USER_CREDENTIALS[unit_personnel_no_access.username]
    ).token(client)
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=unit_personnel_no_access_token,
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # Researcher --> No
    researcher: models.ResearchUser = project.researchusers[0].researchuser
    researcher_token = UserAuth(USER_CREDENTIALS[researcher.username]).token(client)
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=researcher_token,
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_s3_info_errors(client: flask.testing.FlaskClient) -> None:
    """Test errors e.g. SQLAlchemyError and if no info is returned."""
    # Get user
    unituser: models.UnitUser = models.UnitUser.query.first()
    assert unituser

    # Authenticate user
    token = UserAuth(USER_CREDENTIALS[unituser.username]).token(client)

    # Get project
    project: models.Project = unituser.unit.projects[0]

    # Attempt to get S3 info
    with patch("dds_web.api.s3.ApiS3Connector.get_s3_info", mock_sqlalchemyerror):
        response = client.get(
            DDSEndpoint.S3KEYS,
            headers=token,
            query_string={"project": project.public_id},
        )
        assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert "Could not get cloud information" in response.json.get("message")

    with patch("dds_web.api.s3.ApiS3Connector.get_s3_info", mock_get_s3_info_none):
        response = client.get(
            DDSEndpoint.S3KEYS,
            headers=token,
            query_string={"project": project.public_id},
        )
        assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert "No s3 info returned!" in response.json.get("message")


def test_s3info_ok(client: flask.testing.FlaskClient) -> None:
    """Get S3 info."""
    # Get user
    unituser: models.UnitUser = models.UnitUser.query.first()
    assert unituser

    # Authenticate user
    token = UserAuth(USER_CREDENTIALS[unituser.username]).token(client)

    # Get project
    project: models.Project = unituser.unit.projects[0]

    # Get s3 info
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=token,
        query_string={"project": project.public_id},
    )
    assert response.status_code == http.HTTPStatus.OK

    # Verify info
    response_json = response.json
    safespring_project = response_json.get("safespring_project")
    url = response_json.get("url")
    keys = response_json.get("keys")
    bucket = response_json.get("bucket")
    assert all([safespring_project, url, keys, bucket])
    assert safespring_project == project.responsible_unit.safespring_name
    assert url == project.responsible_unit.safespring_endpoint
    assert keys == {
        "access_key": project.responsible_unit.safespring_access,
        "secret_key": project.responsible_unit.safespring_secret,
    }
    assert bucket == project.bucket
