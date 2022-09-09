# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http

# Own
from dds_web import db
from dds_web.database import models
import tests


# CONFIG ################################################################################## CONFIG #

proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}
not_busy_proj_query = {"project": "public_project_id"}
busy_proj_query = {"project": "restricted_project_id"}
# proj_query_restricted = {"project": "restricted_project_id"}

# TESTS #################################################################################### TESTS #


def test_set_busy_no_token(client):
    """Token required to set project busy/not busy."""
    response = client.put(tests.DDSEndpoint.PROJECT_BUSY, headers=tests.DEFAULT_HEADER)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    assert response.json.get("message")
    assert "No token" in response.json.get("message")


def test_set_busy_superadmin_not_allowed(client):
    """Super admin cannot set project busy/not busy."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_BUSY,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_set_busy_no_args(client):
    """Args required to set busy/not busy."""
    # Unit Personnel
    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_BUSY,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing" in response.json.get("message")

    # Unit Admin
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_BUSY,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing" in response.json.get("message")

    # Researcher
    token = tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_BUSY,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing" in response.json.get("message")


def test_set_busy_no_busy(client):
    """busy bool required."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string=not_busy_proj_query,
        json={"something": "notabool"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Missing information about setting busy or not busy." in response.json.get("message")


def test_set_busy_true(client):
    """Set project as busy."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string=not_busy_proj_query,
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    assert f"Project {not_busy_proj_query.get('project')} was set to busy." in response.json.get(
        "message"
    )


def test_set_busy_false(client):
    """Set project as busy."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string=not_busy_proj_query,
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    assert f"The project is already not busy, cannot proceed." in response.json.get("message")


def test_set_busy_false(client):
    """Set project as not busy."""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string=busy_proj_query,
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    assert f"Project {busy_proj_query.get('project')} was set to not busy." in response.json.get(
        "message"
    )


def test_set_busy_project_already_busy(client):
    """Set a busy project as busy."""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.put(
        tests.DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string=busy_proj_query,
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    assert "The project is already busy, cannot proceed." in response.json.get("message")
