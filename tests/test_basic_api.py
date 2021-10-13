# IMPORTS ################################################################################ IMPORTS #

# Standard library
import flask
import http

# Installed
from jwcrypto import jwk, jws

# Own
import tests

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


def test_auth_incorrect_username_and_password_check_statuscode_400_incorrect_info(client):
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


def test_auth_incorrect_password_check_statuscode_400_incorrect_info(client):
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
    assert payload.get("sub") == "username"
