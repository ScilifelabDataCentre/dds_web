# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import json

# Own
import tests
from tests.test_files_new import project_row

# CONFIG ################################################################################## CONFIG #

proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}


def test_set_project_to_available_valid_transition(client):
    """Create project and set status to Available"""

    new_status = {"new_status": "Available"}
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")

    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    project = project_row(project_id=project_id)

    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"


def test_set_project_to_expired_invalid_transition(client):
    """Create project and try to set status to Expired"""

    new_status = {"new_status": "Expired"}
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    project_id = response.json.get("project_id")

    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    project = project_row(project_id=project_id)

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert project.current_status == "In Progress"
