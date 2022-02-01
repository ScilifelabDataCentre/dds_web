# IMPORTS ################################################################################ IMPORTS #

# Standard library
from cryptography.hazmat.primitives.twofactor.hotp import HOTP
import flask
import http
import datetime

# Installed
from jwcrypto import jwk, jws

# Own
import tests
import dds_web
from dds_web import db
from dds_web.security.auth import decrypt_and_verify_token_signature

# TESTS #################################################################################### TESTS #


def test_auth_request_2fa_incorrect_username(client):
    """
    Test that the 2fa endpoint called with incorrect username returns 401/UNAUTHORIZED
    """
    response = client.get(
        tests.DDSEndpoint.REQUEST_EMAIL_2FA,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["wronguser"]).as_tuple(),
    )

    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_request_2fa_incorrect_password(client):
    """
    Test that the 2fa endpoint called with incorrect password returns 401/UNAUTHORIZED
    """
    response = client.get(
        tests.DDSEndpoint.REQUEST_EMAIL_2FA,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["wrongpassword"]).as_tuple(),
    )

    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_request_2fa_correct_credentials(client):
    """
    Test that the 2fa endpoint called with correct credentials returns 200/OK
    """
    response = client.get(
        tests.DDSEndpoint.REQUEST_EMAIL_2FA,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["researcher"]).as_tuple(),
    )

    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("message")
    assert response_json.get("message").startswith("A one-time password has been sent")


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

    response = client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" == response_json.get("message")


def test_auth_incorrect_hotp_counter_statuscode_401_unauthorized(client):
    """Test that the token endpoint with wrong hotp counter returns 401/UNAUTHORIZED"""

    hotp_token_old = tests.UserAuth(tests.USER_CREDENTIALS["researcher"]).fetch_hotp()
    hotp_token_new = tests.UserAuth(tests.USER_CREDENTIALS["researcher"]).fetch_hotp()

    response = client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["researcher"]).as_tuple(),
        json={"HOTP": hotp_token_old.decode()},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid one-time authentication code." == response_json.get("message")


def test_auth_expired_hotp_statuscode_401_unauthorized(client):
    """Test that the token endpoint with wrong expired hotp returns 401/UNAUTHORIZED"""
    user_auth = tests.UserAuth(tests.USER_CREDENTIALS["researcher"])
    hotp_token = user_auth.fetch_hotp()
    user = dds_web.database.models.User.query.filter_by(username=user_auth.username).first()
    user.hotp_issue_time = datetime.datetime.now() - datetime.timedelta(hours=1, seconds=1)
    db.session.commit()

    response = client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["researcher"]).as_tuple(),
        json={"HOTP": hotp_token.decode()},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "One-time authentication code has expired." == response_json.get("message")


def test_auth_correctauth_check_statuscode_200_correct_info(client):
    """Test that the token endpoint called with everything correct returns 200/OK"""
    hotp_token = tests.UserAuth(tests.USER_CREDENTIALS["researcher"]).fetch_hotp()
    response = client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).as_tuple(),
        json={"HOTP": hotp_token.decode()},
    )
    assert response.status_code == http.HTTPStatus.OK
    response_json = response.json
    assert response_json.get("token")
    claims = decrypt_and_verify_token_signature(response_json.get("token"))
    print(claims)
    assert claims["sub"] == "researchuser"


def test_auth_correctauth_reused_hotp_401_unauthorized(client):
    """Test that the token endpoint called with an already used hotp returns 401/UNAUTHORIZED"""
    hotp_token = tests.UserAuth(tests.USER_CREDENTIALS["researcher"]).fetch_hotp()
    response = client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).as_tuple(),
        json={"HOTP": hotp_token.decode()},
    )
    assert response.status_code == http.HTTPStatus.OK

    # Reuse the same hotp token
    response = client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).as_tuple(),
        json={"HOTP": hotp_token.decode()},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid one-time authentication code." == response_json.get("message")


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
        headers={"Authorization": "Bearer made.up.token"},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    response_json = response.json
    assert response_json.get("message")
    assert "Invalid token" == response_json.get("message")


def test_auth_expired_encrypted_token(client):
    """Test that an encrypted expired token returns 401/UNAUTHORIZED"""

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
    """Test that an encrypted token signed with the wrong key returns 401/UNAUTHORIZED"""

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
