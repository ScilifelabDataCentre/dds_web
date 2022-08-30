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


def test_open_troubleshooting_no_response_from_confluence(
    client: flask.testing.FlaskClient,
) -> None:
    """Mock confluence data - none."""
    url: str = "https://scilifelab.atlassian.net/wiki/rest/api/content/2192998470?expand=space,metadata.labels,body.storage"
    status_code: int = 200
    response_json: typing.Dict = None

    problem_page_info = [
        b"Ironically enough it seems that the DDS is having trouble with collecting the troubleshooting information. To proceed:",
        b"The same information can also be found at",
        b"Please notify the Data Centre of this error.",
    ]
    with Mocker() as mock:
        mock.get(url, status_code=status_code, json=response_json)
        response = client.get(tests.DDSEndpoint.TROUBLE, content_type="application/json")
        assert response.status_code == http.HTTPStatus.OK
        assert all([x in response.data for x in problem_page_info])

        response_json: typing.Dict = {}
        mock.get(url, status_code=status_code, json=response_json)
        response = client.get(tests.DDSEndpoint.TROUBLE, content_type="application/json")
        assert response.status_code == http.HTTPStatus.OK
        assert all([x in response.data for x in problem_page_info])


def test_open_troubleshooting_500(client: flask.testing.FlaskClient) -> None:
    """Mock confluence data - none."""
    url: str = "https://scilifelab.atlassian.net/wiki/rest/api/content/2192998470?expand=space,metadata.labels,body.storage"
    status_code: int = 500
    response_json: typing.Dict = None
    problem_page_info = [
        b"Ironically enough it seems that the DDS is having trouble with collecting the troubleshooting information. To proceed:",
        b"The same information can also be found at",
        b"Please notify the Data Centre of this error.",
    ]
    with Mocker() as mock:
        mock.get(url, status_code=status_code, json=response_json)
        response = client.get(tests.DDSEndpoint.TROUBLE, content_type="application/json")
        assert response.status_code == http.HTTPStatus.OK
        assert all([x in response.data for x in problem_page_info])


def test_open_troubleshooting(client: flask.testing.FlaskClient) -> None:
    """Mock confluence data and display on page."""
    url: str = "https://scilifelab.atlassian.net/wiki/rest/api/content/2192998470?expand=space,metadata.labels,body.storage"
    status_code: int = 200
    response_json: typing.Dict = {
        "body": {"storage": {"value": "This is some data that should be displayed"}}
    }
    with Mocker() as mock:
        mock.get(url, status_code=status_code, json=response_json)
        response = client.get(tests.DDSEndpoint.TROUBLE, content_type="application/json")
        assert response.status_code == http.HTTPStatus.OK
        assert b"<h1>Troubleshooting</h1>" in response.data


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
