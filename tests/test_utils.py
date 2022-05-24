from simplejson import JSONDecodeError

from werkzeug.exceptions import BadRequest, InternalServerError

from flask.testing import FlaskClient

from pytest import raises
from requests_mock.mocker import Mocker

from dds_web.utils import validate_cli_version


url: str = "http://localhost"
pypi_api_url: str = "https://pypi.python.org/pypi/dds-cli/json"


def test_validate_cli_version_without_custom_header(client: FlaskClient):
    with client.session_transaction() as session:
        assert validate_cli_version() == (False, 400, "err0")


def test_validate_cli_version_with_custom_header(client: FlaskClient):
    with Mocker() as mock:
        mock.get(url, status_code=200, json={})
        mock.get(pypi_api_url, status_code=200, json={"info": {"version": "0.0.0"}})
        client.get(url, headers={"Cache-Control": "no-cache", "X-CLI-Version": "0.0.0"})

        assert validate_cli_version() == (True, 200, None)


def test_validate_cli_version_with_custom_header_0_0_0(client: FlaskClient):
    with Mocker() as mock:
        mock.get(url, status_code=200, json={})
        mock.get(pypi_api_url, status_code=200, json={"info": {"version": "1.0.0"}})
        with raises(BadRequest) as exc_info:
            client.get(url, headers={"Cache-Control": "no-cache", "X-CLI-Version": "0.0.0"})

            assert validate_cli_version() == (False, 400, "err2")

        assert len(exc_info.value.args) == 0


def test_validate_cli_version_with_custom_header_0_1_0(client: FlaskClient):
    with Mocker() as mock:
        mock.get(url, status_code=200, json={})
        mock.get(pypi_api_url, status_code=200, json={"info": {"version": "0.2.0"}})
        client.get(url, headers={"Cache-Control": "no-cache", "X-CLI-Version": "0.1.0"})

        assert validate_cli_version() == (True, 200, "err3")


def test_validate_cli_version_with_custom_header_json_decode_error(client: FlaskClient):
    with Mocker() as mock:
        mock.get(url, status_code=200, json={})
        mock.get(pypi_api_url, status_code=200, text="")
        with raises(InternalServerError) as exc_info:
            client.get(url, headers={"Cache-Control": "no-cache", "X-CLI-Version": "0.0.0"})

            assert validate_cli_version() == (False, 500, "err1")

        assert len(exc_info.value.args) == 0


def test_validate_cli_version_with_custom_header_error(client: FlaskClient):
    with Mocker() as mock:
        mock.get(url, status_code=200, json={})
        mock.get(pypi_api_url, status_code=200, json={})
        with raises(InternalServerError) as exc_info:
            client.get(url, headers={"Cache-Control": "no-cache", "X-CLI-Version": "0.1.0"})

            assert validate_cli_version() == (False, 500, "err1")

        assert len(exc_info.value.args) == 0
