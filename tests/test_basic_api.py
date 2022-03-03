# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import datetime
import time
import unittest

# Installed
import flask
import flask_mail
import pytest

# Own
import tests
import dds_web
from dds_web import db
from dds_web.security.auth import decrypt_and_verify_token_signature
from dds_web.security.tokens import encrypted_jwt_token


# TESTS #################################################################################### TESTS #

# Partial Token #################################################################### Partial Token #
def test_auth_check_statuscode_401_missing_info(client):
    """
    Test that the token endpoint called without parameters returns 401/UNAUTHORIZED
    """

    # No params, no auth
    response = client.get(tests.DDSEndpoint.ENCRYPTED_TOKEN)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" in response_json.get("message")


def test_auth_no_username_check_statuscode_401_incorrect_info(client):
    """Test that the token endpoint called with blank username and password returns 401/UNAUTHORIZED."""

    response = client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["nouser"]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_no_password_check_statuscode_401_incorrect_info(client):
    """Test that the token endpoint called with empty password returns 401/UNAUTHORIZED"""

    response = client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["nopassword"]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_incorrect_username_check_statuscode_401_incorrect_info(client):
    """Test that the token endpoint called with incorrect username returns 401/UNAUTHORIZED"""

    response = client.get(tests.DDSEndpoint.ENCRYPTED_TOKEN, auth=("", "password"))
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_correct_credentials(client):
    """Test that the token endpoint called correctly returns a token and sends an email."""

    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.get(tests.DDSEndpoint.ENCRYPTED_TOKEN, auth=("researchuser", "password"))
        assert mock_mail_send.call_count == 1
    assert response.status_code == http.HTTPStatus.OK

    # Shouldn't send an email shortly after the first
    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.get(tests.DDSEndpoint.ENCRYPTED_TOKEN, auth=("researchuser", "password"))
        assert mock_mail_send.call_count == 0


# Second Factor ################################################################### Second Factor #


def test_auth_second_factor_empty(client):
    user_auth = tests.UserAuth(tests.USER_CREDENTIALS["researcher"])

    response = client.get(
        tests.DDSEndpoint.SECOND_FACTOR,
        headers={"Authorization": f"Bearer made.up.token.long.version"},
    )

    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert "Invalid token" == response_json.get("message")


# HOTP ##################################################################################### HOTP #


def test_auth_second_factor_incorrect_token(client):
    """
    Test that the two_factor endpoint called with incorrect partial token returns 401/UNAUTHORIZED
    """
    user_auth = tests.UserAuth(tests.USER_CREDENTIALS["researcher"])

    hotp_token = user_auth.fetch_hotp()

    response = client.get(
        tests.DDSEndpoint.SECOND_FACTOR,
        headers={"Authorization": f"Bearer made.up.token.long.version"},
        json={"HOTP": hotp_token.decode()},
    )

    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid token" == response_json.get("message")


def test_auth_second_factor_incorrect_hotp_counter_statuscode_401_unauthorized(client):
    """Test that the second_factor endpoint with wrong hotp counter returns 401/UNAUTHORIZED"""
    user_auth = tests.UserAuth(tests.USER_CREDENTIALS["researcher"])

    hotp_token_old = user_auth.fetch_hotp()
    hotp_token_new = user_auth.fetch_hotp()

    response = client.get(
        tests.DDSEndpoint.SECOND_FACTOR,
        headers=user_auth.partial_token(client),
        json={"HOTP": hotp_token_old.decode()},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid one-time authentication code." == response_json.get("message")


def test_auth_second_factor_incorrect_token(client):
    """
    Test that the two_factor endpoint called with a password_reset token returns 401/UNAUTHORIZED and
    does not send a mail.
    """
    user_auth = tests.UserAuth(tests.USER_CREDENTIALS["researcher"])

    hotp_token = user_auth.fetch_hotp()

    reset_token = encrypted_jwt_token(
        username="researchuser",
        sensitive_content=None,
        expires_in=datetime.timedelta(
            seconds=3600,
        ),
        additional_claims={"rst": "pwd"},
    )

    response = client.get(
        tests.DDSEndpoint.SECOND_FACTOR,
        headers={"Authorization": f"Bearer {reset_token}"},
        json={"HOTP": hotp_token.decode()},
    )

    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid token" == response_json.get("message")


def test_auth_second_factor_expired_hotp_statuscode_401_unauthorized(client):
    """Test that the second_factor endpoint with expired hotp returns 401/UNAUTHORIZED"""
    user_auth = tests.UserAuth(tests.USER_CREDENTIALS["researcher"])
    hotp_token = user_auth.fetch_hotp()
    user = dds_web.database.models.User.query.filter_by(username=user_auth.username).first()
    user.hotp_issue_time = datetime.datetime.now() - datetime.timedelta(minutes=15, seconds=1)
    db.session.commit()

    response = client.get(
        tests.DDSEndpoint.SECOND_FACTOR,
        headers=user_auth.partial_token(client),
        json={"HOTP": hotp_token.decode()},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid one-time authentication code." == response_json.get("message")


def test_auth_second_factor_correctauth_check_statuscode_200_correct_info(client):
    """Test that the second_factor endpoint called with everything correct returns 200/OK"""
    user_auth = tests.UserAuth(tests.USER_CREDENTIALS["researcher"])
    hotp_token = user_auth.fetch_hotp()
    response = client.get(
        tests.DDSEndpoint.SECOND_FACTOR,
        headers=user_auth.partial_token(client),
        json={"HOTP": hotp_token.decode()},
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("token")
    claims = decrypt_and_verify_token_signature(response_json.get("token"))
    print(claims)
    assert claims["sub"] == "researchuser"


def test_auth_second_factor_correctauth_reused_hotp_401_unauthorized(client):
    """Test that the token endpoint called with an already used hotp returns 401/UNAUTHORIZED"""
    user_auth = tests.UserAuth(tests.USER_CREDENTIALS["researcher"])
    hotp_token = user_auth.fetch_hotp()
    response = client.get(
        tests.DDSEndpoint.SECOND_FACTOR,
        headers=user_auth.partial_token(client),
        json={"HOTP": hotp_token.decode()},
    )
    assert response.status_code == http.HTTPStatus.OK

    # Reuse the same hotp token
    response = client.get(
        tests.DDSEndpoint.SECOND_FACTOR,
        headers=user_auth.partial_token(client),
        json={"HOTP": hotp_token.decode()},
    )

    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid one-time authentication code." == response_json.get("message")


# TOTP ##################################################################################### TOTP #


@pytest.fixture()
def totp_for_user(client):
    """Create a user with TOTP enabled and return TOTP object"""
    user = dds_web.database.models.User.query.filter_by(username="researchuser").first()
    user.setup_totp_secret()
    user.activate_totp()
    return user.totp_object()


def test_auth_second_factor_TOTP_incorrect_token(client, totp_for_user):
    """
    Test that the two_factor endpoint called with incorrect partial token returns 401/UNAUTHORIZED
    """
    user_auth = tests.UserAuth(tests.USER_CREDENTIALS["researcher"])

    totp_token = totp_for_user.generate(time.time())

    response = client.get(
        tests.DDSEndpoint.SECOND_FACTOR,
        headers={"Authorization": f"Bearer made.up.token.long.version"},
        json={"TOTP": totp_token.decode()},
    )

    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid token" == response_json.get("message")


# Token Authentication ##################################################### Token Authentication #


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
    """Test that a made up token returns 401/UNAUTHORIZED"""

    # Fetch the project public key as an example
    response = client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        query_string={"project": "public_project_id"},
        headers={"Authorization": "Bearer made.up.token.long.version"},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid token" == response_json.get("message")


def test_auth_expired_encrypted_token(client):
    """Test that an encrypted expired token returns 401/UNAUTHORIZED"""

    token = dds_web.api.user.encrypted_jwt_token(
        username="researchuser", sensitive_content=None, expires_in=datetime.timedelta(hours=-2)
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
    """Test that an encrypted token signed with the wrong key returns 401/UNAUTHORIZED"""

    old_secret = flask.current_app.config.get("SECRET_KEY")
    flask.current_app.config["SECRET_KEY"] = "XX" * 16
    token = dds_web.api.user.encrypted_jwt_token(
        username="researchuser", sensitive_content=None, expires_in=datetime.timedelta(hours=-2)
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
