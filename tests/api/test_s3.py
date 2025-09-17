import flask
import http
import sqlalchemy
import typing
import pytest
from unittest.mock import patch, MagicMock

from tests import DDSEndpoint, DEFAULT_HEADER, UserAuth, USER_CREDENTIALS
from dds_web.database import models
from dds_web import db
from dds_web.api import api_s3_connector

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
        "safespring_project": project.responsible_unit.sto2_name,
        "url": project.responsible_unit.sto2_endpoint,
        "keys": {
            "access_key": project.responsible_unit.sto2_access,
            "secret_key": project.responsible_unit.sto2_secret,
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


def test_get_s3_sql_error(client):

    # Get project
    project: models.Project = models.Project.query.first()

    # Get users with access to project
    unit_users = db.session.query(models.UnitUser).filter(
        models.UnitUser.unit_id == project.unit_id
    )

    # Mock the s3 connector and exception
    mock_conector = MagicMock()
    with patch("dds_web.api.api_s3_connector.ApiS3Connector.get_s3_info", mock_conector):
        mock_conector.side_effect = sqlalchemy.exc.SQLAlchemyError("Database error")

        # Try s3info - "/s3/proj"
        unit_personnel: models.UnitUser = unit_users.filter(
            models.UnitUser.is_admin == False
        ).first()
        unit_personnel_token = UserAuth(USER_CREDENTIALS[unit_personnel.username]).token(client)
        response = client.get(
            DDSEndpoint.S3KEYS,
            headers=unit_personnel_token,
            query_string={"project": "public_project_id"},
        )
        assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert "Could not get cloud information" in response.json["message"]


def test_get_s3_empty_response(client):

    # Get project
    project: models.Project = models.Project.query.first()

    # Get users with access to project
    unit_users = db.session.query(models.UnitUser).filter(
        models.UnitUser.unit_id == project.unit_id
    )

    # Mock the s3 connector and exception
    mock_conector = MagicMock()
    with patch("dds_web.api.api_s3_connector.ApiS3Connector.get_s3_info", mock_conector):
        mock_conector.return_value = (None, None, None, None)

        # Try s3info - "/s3/proj"
        unit_personnel: models.UnitUser = unit_users.filter(
            models.UnitUser.is_admin == False
        ).first()
        unit_personnel_token = UserAuth(USER_CREDENTIALS[unit_personnel.username]).token(client)
        response = client.get(
            DDSEndpoint.S3KEYS,
            headers=unit_personnel_token,
            query_string={"project": "public_project_id"},
        )
        assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert "No s3 info returned!" in response.json["message"]

def test_connect_cloud_decorator_initializes_resource(client):
    """Verify that the connect_cloud decorator creates an s3 resource."""

    # Get project
    project: models.Project = models.Project.query.first()

    # Mock session and resource creation and name them for easier debugging
    session_mock = MagicMock(name="session")
    resource_mock = MagicMock(name="resource")

    # Patch the methods used in the decorator
    with (
        patch(
            "dds_web.api.api_s3_connector.ApiS3Connector.get_s3_info",
            return_value=(
                "name",
                {"access_key": "ak", "secret_key": "sk"},
                "https://endpoint",
                "bucket",
            ),
        ) as mock_get_s3_info,
        patch("dds_web.api.dds_decorators.boto3.session.Session") as mock_session_ctor,
        patch("dds_web.api.dds_decorators.create_s3_resource") as mock_create_resource,
    ):
        mock_session_ctor.return_value = session_mock
        mock_create_resource.return_value = resource_mock

        # Use the connector in a with statement to trigger the decorator
        with api_s3_connector.ApiS3Connector(project=project) as connector:
            pass

    # Verify that the methods were called and the resource was set
    mock_get_s3_info.assert_called_once_with()
    mock_session_ctor.assert_called_once_with()
    mock_create_resource.assert_called_once_with(
        endpoint_url="https://endpoint",
        access_key="ak",
        secret_key="sk",
        session=session_mock,
    )
    assert connector.resource is resource_mock