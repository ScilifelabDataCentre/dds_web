# IMPORTS ################################################################################ IMPORTS #

# Standard library
import flask
import http
import datetime

# Installed
from jwcrypto import jwk, jws

# Own
import tests
import dds_web
from dds_web.api.user import encrypted_jwt_token, jwt_token

# TESTS #################################################################################### TESTS #


def test_auth_check_statuscode_401_missing_info(client):
    """
    Test that the auth endpoint returns:
    Status code: 401/UNAUTHORIZED
    Message: Missing or incorrect credentials
    """

    # No params, no auth
    response = client.get(tests.DDSEndpoint.TOKEN)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" in response_json.get("message")


def test_auth_incorrect_username_check_statuscode_401_incorrect_info(client):
    """Test that the auth endpoint returns
    Status code: 401/UNAUTHORIZED
    Message: Missing or incorrect credentials
    """

    response = client.get(
        tests.DDSEndpoint.TOKEN, auth=tests.UserAuth(tests.USER_CREDENTIALS["nouser"]).as_tuple()
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_incorrect_username_and_password_check_statuscode_401_incorrect_info(client):
    """Test that the auth endpoint returns
    Status code: 401/UNAUTHORIZED
    Message: Missing or incorrect credentials
    """

    response = client.get(
        tests.DDSEndpoint.TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["nopassword"]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_incorrect_password_check_statuscode_401_incorrect_info(client):
    """Test that the auth endpoint returns
    Status code: 401/UNAUTHORIZED
    Message: Missing or incorrect credentials
    """

    response = client.get(
        tests.DDSEndpoint.TOKEN, auth=tests.UserAuth(tests.USER_CREDENTIALS["wronguser"]).as_tuple()
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_correctauth_check_statuscode_200_correct_info(client):
    """Test that the auth endpoint returns
    Status code: 200/OK
    Token: includes the authenticated username
    """

    response = client.get(
        tests.DDSEndpoint.TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("token")
    jwstoken = jws.JWS()
    jwstoken.deserialize(response_json.get("token"))
    jwstoken.verify(jwk.JWK.from_password(flask.current_app.config.get("SECRET_KEY")))
    # extracting JWS token payload before verification will raise a `InvalidJWSOperation` error
    payload = jws.json_decode(jwstoken.payload)
    assert (
        payload.get("sub") == tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).as_tuple()[0]
    )


def test_auth_incorrect_token_without_periods(client):
    """Test that a malformatted token returns unauthorized"""

    # Fetch the project public key as an example
    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        query_string={"project": "public_project_id"},
        headers={"Authorization": "Bearer " + "madeuptoken"},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid token" == response_json.get("message")


def test_auth_incorrect_token_with_periods(client):
    """Test that a made up token returns unauthorized"""

    # Fetch the project public key as an example
    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        query_string={"project": "public_project_id"},
        headers={"Authorization": "Bearer made.up.token"},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid token" == response_json.get("message")


def test_auth_expired_signed_token(client):
    """Test that an signed expired token returns unauthorized"""

    token = dds_web.api.user.jwt_token("researchuser", expires_in=datetime.timedelta(hours=-2))
    # Fetch the project public key as an example
    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        query_string={"project": "public_project_id"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Expired token" == response_json.get("message")


def test_auth_token_wrong_secret_key_signed_token(client):
    """Test that an encrypted token signed with the wrong key returns unauthorized"""

    old_secret = flask.current_app.config.get("SECRET_KEY")
    flask.current_app.config["SECRET_KEY"] = "XX" * 16
    token = dds_web.api.user.jwt_token("researchuser", expires_in=datetime.timedelta(hours=-2))
    # reset secret key
    flask.current_app.config["SECRET_KEY"] = old_secret

    # Fetch the project public key as an example
    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        query_string={"project": "public_project_id"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid token" == response_json.get("message")


def test_auth_with_token(client):
    """Test that token can be used for authentication"""
    response = client.get(
        tests.DDSEndpoint.TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("token")

    # Fetch the project public key as an example
    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        query_string={"project": "public_project_id"},
        headers={"Authorization": "Bearer " + response_json.get("token")},
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("public")


# ENCRYPTED TOKEN ################################################################ ENCRYPTED TOKEN #


def test_auth_expired_encrypted_token(client):
    """Test that an encrypted expired token returns unauthorized"""

    token = dds_web.api.user.encrypted_jwt_token(
        "researchuser", None, expires_in=datetime.timedelta(hours=-2)
    )
    # Fetch the project public key as an example
    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        query_string={"project": "public_project_id"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Expired token" == response_json.get("message")


def test_auth_token_wrong_secret_key_encrypted_token(client):
    """Test that an encrypted token signed with the wrong key returns unauthorized"""

    old_secret = flask.current_app.config.get("SECRET_KEY")
    flask.current_app.config["SECRET_KEY"] = "XX" * 16
    token = dds_web.api.user.encrypted_jwt_token(
        "researchuser", None, expires_in=datetime.timedelta(hours=-2)
    )
    # reset secret key
    flask.current_app.config["SECRET_KEY"] = old_secret

    # Fetch the project public key as an example
    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        query_string={"project": "public_project_id"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid token" == response_json.get("message")


def test_auth_with_encrypted_token(client):
    """Test that token can be used for authentication"""
    response = client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("token")

    # Fetch the project public key as an example
    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        query_string={"project": "public_project_id"},
        headers={"Authorization": "Bearer " + response_json.get("token")},
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("public")
