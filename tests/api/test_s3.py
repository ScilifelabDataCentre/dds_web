import flask
import http
import sqlalchemy
import typing

from tests import DDSEndpoint, DEFAULT_HEADER, UserAuth, USER_CREDENTIALS
from dds_web.database import models
from dds_web import db


def test_get_s3_info_unauthorized(client: flask.testing.FlaskClient) -> None:
    """Only Unit Admin and Unit Personnel can get this info."""
    # Get project
    project: models.Project = models.Project.query.first()

    # Get users with access to project
    unit_users = db.session.query(models.UnitUser).filter(
        models.UnitUser.unit_id == project.unit_id
    )

    # Get users with no access to project
    unit_users_no_access = db.session.query(models.UnitUser).filter(models.UnitUser.unit_id != project.unit_id)

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
    # Super Admin: No
    super_admin_token = UserAuth(USER_CREDENTIALS["superadmin"]).token(client)
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=super_admin_token,
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # Unit Admin, correct unit: Yes
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

    # Unit Admin, incorrect unit: No
    unit_admin_no_access: models.UnitUser = unit_users_no_access.filter(models.UnitUser.is_admin == True).first()
    unit_admin_no_access_token: UserAuth(USER_CREDENTIALS[unit_admin_no_access.username]).token(client)
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=unit_admin_no_access_token,
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # Unit Personnel, correct unit: Yes
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

    # Unit Personnel, incorrect unit: No
    unit_personnel_no_access: models.UnitUser = unit_users_no_access.filter(models.UnitUser.is_admin == False).first()
    unit_personnel_no_access_token: UserAuth(USER_CREDENTIALS[unit_personnel_no_access.username]).token(client)
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=unit_personnel_no_access_token,
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # Researcher: No
    researcher: models.ResearchUser = project.researchusers[0].researchuser
    researcher_token = UserAuth(USER_CREDENTIALS[researcher.username]).token(client)
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=researcher_token,
        query_string={"project": "public_project_id"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
