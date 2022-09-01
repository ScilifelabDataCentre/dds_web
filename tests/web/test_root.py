import http
import typing
import flask.testing
import tests
import pathlib
from requests_mock.mocker import Mocker
import unittest
import requests

# home, /


def test_home_post(client: flask.testing.FlaskClient) -> None:
    """Post should not work."""

    response = client.post(tests.DDSEndpoint.INDEX, content_type="application/json")
    assert response.status_code == http.HTTPStatus.METHOD_NOT_ALLOWED


def test_home(client: flask.testing.FlaskClient) -> None:
    """Home page with log in form should be displayed."""
    response = client.get(tests.DDSEndpoint.INDEX, content_type="application/json")
    assert response.status_code == http.HTTPStatus.OK
    assert "text/html" in response.content_type
    assert b"<title>Data Delivery System</title>" in response.data
    assert all(
        x in response.data
        for x in [
            b"Log In</h1>",
            b'<label for="username">Username</label>',
            b'<label for="password">Password</label>',
        ]
    )


# open_policy, /policy


def test_open_policy_post(client: flask.testing.FlaskClient) -> None:
    """Post should not work."""
    response = client.post(tests.DDSEndpoint.POLICY, content_type="application/json")
    assert response.status_code == http.HTTPStatus.METHOD_NOT_ALLOWED


def test_open_policy(client: flask.testing.FlaskClient) -> None:
    """Open policy document."""
    response = client.get(tests.DDSEndpoint.POLICY, content_type="application/json")
    assert response.status_code == http.HTTPStatus.OK
    assert "text/html" in response.content_type
    with (pathlib.Path.cwd() / pathlib.Path("dds_web/templates/policy.html")).open(
        mode="rb"
    ) as file:
        for x in file.readlines():
            if b"{%" not in x:
                assert x in response.data


# open_troubleshooting


def test_open_troubleshooting_post(client: flask.testing.FlaskClient) -> None:
    """Post should not work."""
    response = client.post(tests.DDSEndpoint.TROUBLE, content_type="application/json")
    assert response.status_code == http.HTTPStatus.METHOD_NOT_ALLOWED


# get status


def test_get_status_post(client: flask.testing.FlaskClient) -> None:
    """Post should not work."""
    response = client.post(tests.DDSEndpoint.STATUS, content_type="application/json")
    assert response.status_code == http.HTTPStatus.METHOD_NOT_ALLOWED


def test_get_status(client: flask.testing.FlaskClient) -> None:
    """Get status."""
    response = client.get(tests.DDSEndpoint.STATUS, content_type="application/json")
    assert response.status_code == http.HTTPStatus.OK

    assert response.json == {"status": "ready"}
