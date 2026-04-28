import datetime
import socket
import smtplib
import unittest.mock

import flask
import flask_mail
from http import HTTPStatus
import werkzeug
from typing import Dict

from tests import UserAuth, USER_CREDENTIALS, DDSEndpoint, DEFAULT_HEADER

from dds_web.security.tokens import encrypted_jwt_token


def successful_web_login(client: flask.testing.FlaskClient, user_auth: UserAuth):
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.LOGIN, headers=DEFAULT_HEADER
    )
    assert response.status_code == HTTPStatus.OK

    form_token: str = flask.g.csrf_token

    form_data: Dict = {
        "csrf_token": form_token,
        "username": user_auth.as_tuple()[0],
        "password": user_auth.as_tuple()[1],
        "submit": "Login",
    }

    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.LOGIN,
        json=form_data,
        follow_redirects=True,
        headers=DEFAULT_HEADER,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.request.path == DDSEndpoint.CONFIRM_2FA

    form_token: str = flask.g.csrf_token

    form_data: Dict = {
        "csrf_token": form_token,
        "hotp": user_auth.fetch_hotp().decode(),
        "submit": "Authenticate",
    }

    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.CONFIRM_2FA,
        json=form_data,
        follow_redirects=True,
        headers=DEFAULT_HEADER,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.request.path == DDSEndpoint.INDEX
    assert response.request.path == flask.url_for("pages.home")

    return form_token


def test_load_login_page(client: flask.testing.FlaskClient):
    user_auth: UserAuth = UserAuth(USER_CREDENTIALS["researcher"])

    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.LOGIN, headers=DEFAULT_HEADER
    )
    assert response.status_code == HTTPStatus.OK


def test_cancel_2fa(client: flask.testing.FlaskClient):
    user_auth = UserAuth(USER_CREDENTIALS["researcher"])

    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.LOGIN, headers=DEFAULT_HEADER
    )
    assert response.status_code == HTTPStatus.OK

    form_token: str = flask.g.csrf_token

    form_data: Dict = {
        "csrf_token": form_token,
        "username": user_auth.as_tuple()[0],
        "password": user_auth.as_tuple()[1],
        "submit": "Login",
    }

    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.LOGIN,
        json=form_data,
        follow_redirects=True,
        headers=DEFAULT_HEADER,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.request.path == DDSEndpoint.CONFIRM_2FA

    second_factor_token: str = flask.session.get("2fa_initiated_token")
    assert second_factor_token is not None

    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.CANCEL_2FA,
        follow_redirects=True,
        headers=DEFAULT_HEADER,
    )

    assert response.status_code == HTTPStatus.OK
    assert response.request.path == DDSEndpoint.LOGIN

    second_factor_token: str = flask.session.get("2fa_initiated_token")
    assert second_factor_token is None


def test_password_reset(client: flask.testing.FlaskClient):
    user_auth: UserAuth = UserAuth(USER_CREDENTIALS["researcher"])
    successful_web_login(client, user_auth)
    headers: Dict = user_auth.token(client)

    token: str = encrypted_jwt_token(
        username="researchuser",
        sensitive_content=b"".hex(),
        expires_in=datetime.timedelta(hours=24),
        additional_claims={"inv": "researchuser", "rst": "pwd"},
    )

    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.USER_INFO,
        headers=headers,
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.request.path == DDSEndpoint.USER_INFO

    form_token: str = flask.g.csrf_token

    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.LOGOUT, follow_redirects=True, headers=headers
    )
    assert response.status_code == HTTPStatus.OK
    assert response.request.path == DDSEndpoint.INDEX

    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.REQUEST_RESET_PASSWORD,
        headers={"Content-Type": "application/x-www-form-urlencoded", **DEFAULT_HEADER},
        data={
            "csrf_token": form_token,
            "email": "researchuser@mailtrap.io",
        },
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.content_type == "text/html; charset=utf-8"
    assert response.request.path == DDSEndpoint.INDEX

    response: werkzeug.test.WrapperTestResponse = client.post(
        f"{DDSEndpoint.REQUEST_RESET_PASSWORD}/{token}",
        headers={"Content-Type": "application/x-www-form-urlencoded", **DEFAULT_HEADER},
        data={
            "csrf_token": form_token,
            "password": "Password1!",
            "confirm_password": "Password1!",
        },
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.content_type == "text/html; charset=utf-8"
    assert response.request.path == DDSEndpoint.PASSWORD_RESET_COMPLETED

    with client.session_transaction() as session:
        session["reset_token"] = token

    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PASSWORD_RESET_COMPLETED,
        follow_redirects=True,
        headers=DEFAULT_HEADER,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.content_type == "text/html; charset=utf-8"
    assert response.request.path == DDSEndpoint.PASSWORD_RESET_COMPLETED

    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.USER_INFO,
        headers=headers,
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.content_type == "application/json"
    assert response.request.path == DDSEndpoint.USER_INFO
    assert (
        response.json.get("message")
        == "Password reset performed after last authentication. Start a new authenticated session to proceed."
    )


# Web /login resilience when the HOTP email cannot be sent ###################
#
# When mail.send fails (e.g. transient SMTP / DNS hiccup), the /login POST
# handler must:
#   - not return 500
#   - not advance the user to the /confirm_2fa page
#   - not put a 2fa_initiated_token in the session
#   - flash a user-facing message
# We exercise the three failure modes that send_hotp_email now catches.


def _post_login_with_failing_mail(
    client: flask.testing.FlaskClient, side_effect: Exception
):
    """Helper: post valid credentials to /login while mail.send raises side_effect."""
    user_auth = UserAuth(USER_CREDENTIALS["researcher"])

    # Prime CSRF token
    response = client.get(DDSEndpoint.LOGIN, headers=DEFAULT_HEADER)
    assert response.status_code == HTTPStatus.OK
    form_token: str = flask.g.csrf_token

    form_data: Dict = {
        "csrf_token": form_token,
        "username": user_auth.as_tuple()[0],
        "password": user_auth.as_tuple()[1],
        "submit": "Login",
    }

    with unittest.mock.patch.object(
        flask_mail.Mail, "send", side_effect=side_effect
    ) as mock_mail_send:
        response = client.post(
            DDSEndpoint.LOGIN,
            json=form_data,
            follow_redirects=True,
            headers=DEFAULT_HEADER,
        )
        assert mock_mail_send.call_count == 1

    return response


def _assert_redirected_back_to_login(client, response):
    """Common assertions for the failure path."""
    # Followed redirects -- final page is /login again, not /confirm_2fa.
    assert response.status_code == HTTPStatus.OK
    assert response.request.path == DDSEndpoint.LOGIN

    # No 2fa token leaked into the session -- the user has no code anyway.
    with client.session_transaction() as session:
        assert "2fa_initiated_token" not in session

    # The flashed message is rendered into the page; assert the user sees it.
    body = response.data.decode("utf-8", errors="replace")
    assert "could not send your one-time code" in body.lower()


def test_login_redirects_back_when_mail_dns_fails(client):
    """socket.gaierror (DNS lookup failure) on mail.send must not 500."""
    response = _post_login_with_failing_mail(
        client, side_effect=socket.gaierror(-3, "Try again")
    )
    _assert_redirected_back_to_login(client, response)


def test_login_redirects_back_when_smtp_fails(client):
    """smtplib.SMTPException must not 500."""
    response = _post_login_with_failing_mail(
        client, side_effect=smtplib.SMTPException("relay rejected message")
    )
    _assert_redirected_back_to_login(client, response)


def test_login_redirects_back_when_socket_oserror(client):
    """Generic OSError (e.g. connection reset) must not 500."""
    response = _post_login_with_failing_mail(
        client, side_effect=OSError("connection reset by peer")
    )
    _assert_redirected_back_to_login(client, response)
