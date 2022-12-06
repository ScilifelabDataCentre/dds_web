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

    # Get users with access
    unit_users = db.session.query(models.UnitUser).filter(models.UnitUser.unit_id == project.unit_id)
    unit_admin: models.UnitUser = unit_users.filter(models.UnitUser.is_admin == True).first()
    unit_personnel: models.UnitUser = unit_users.filter(models.UnitUser.is_admin == False).first()
    researcher: models.ResearchUser = project.researchusers[0].researchuser

    # Authenticate different users
    super_admin_token = UserAuth(USER_CREDENTIALS["superadmin"]).token(client)
    unit_admin_token = UserAuth(USER_CREDENTIALS[unit_admin.username]).token(client)
    unit_personnel_token = UserAuth(USER_CREDENTIALS[unit_personnel.username]).token(client)
    researcher_token = UserAuth(USER_CREDENTIALS[researcher.username]).token(client)

    # Returned info - expected
    expected_return: typing.Dict = {
        "safespring_project": project.responsible_unit.safespring_name, 
        "url": project.responsible_unit.safespring_endpoint,
        "keys": {"access_key": project.responsible_unit.safespring_access, "secret_key": project.responsible_unit.safespring_secret}, 
        "bucket": project.bucket
    }

    # Try s3info - "/s3/proj"
    # Super Admin: No
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=super_admin_token,
        query_string={"project": "public_project_id"},  
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # Unit Admin: Yes
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

    # Unit Personnel: Yes
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

    # Researcher: No
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=researcher_token,
        query_string={"project": "public_project_id"},  
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN