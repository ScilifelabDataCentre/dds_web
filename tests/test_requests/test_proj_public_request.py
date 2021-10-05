# IMPORTS ################################################################################ IMPORTS #
# Standard library

# Installed
import http

# Own modules
import tests as dds_cli
from tests import user

# from tests.conftest import client

# VARIABLES ############################################################################ VARIABLES #


# TESTS #################################################################################### TESTS #


def test_proj_public_no_token(client):
    """Attempting to get the public key without a token should not work"""

    response = client.get(dds_cli.DDSEndpoint.PROJ_PUBLIC)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json()
    assert "Missing or incorrect credentials" in response_json.get("message")


def test_proj_public_no_project(client):
    """Attempting to get public key without a project should not work"""

    token = user.User(username="username", password="password").token
    response = client.get(dds_cli.DDSEndpoint.PROJ_PUBLIC, headers=token)
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    response_json = response.json()
    assert "without project ID" in response_json.get("message")


def test_proj_public_insufficient_credentials(client):
    """If the project access has not been granted, the public key should not be provided."""

    token = user.User(username="admin", password="password").token
    response = client.get(
        dds_cli.DDSEndpoint.PROJ_PUBLIC, params={"project": "public_project_id"}, headers=token
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    response_json = response.json()
    assert "not have permission" in response_json.get("message")


def test_project_public_researcher_get(client):
    """User should get access to public key"""

    token = user.User(username="username", password="password").token
    response = client.get(
        dds_cli.DDSEndpoint.PROJ_PUBLIC, params={"project": "public_project_id"}, headers=token
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json()
    assert response_json.get("public")


def test_project_public_facility_put(client):
    """User should get access to public key"""

    token = user.User(username="facility", password="password").token
    response = client.get(
        dds_cli.DDSEndpoint.PROJ_PUBLIC, params={"project": "public_project_id"}, headers=token
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json()
    assert response_json.get("public")
