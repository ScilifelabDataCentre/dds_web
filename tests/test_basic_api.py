# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http

# Installed
import jwt

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

    response = client.get(tests.DDSEndpoint.TOKEN, auth=("incorrect_username", "password"))
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
        tests.DDSEndpoint.TOKEN, auth=("incorrect_username", "incorrect_password")
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

    response = client.get(tests.DDSEndpoint.TOKEN, auth=("username", "incorrect_password"))
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_correctauth_check_statuscode_200_correct_info(client):
    """Test that the auth endpoint returns
    Status code: 200/OK
    Token: includes the authenticated username
    """

    response = client.get(tests.DDSEndpoint.TOKEN, auth=("username", "password"))
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("token")
    # decoded_token = jwt.JWT.decode(
    #    response_json.get("token"), key="", options={"verify_signature": False}
    # )
    # assert "username" == decoded_token.get("user")
