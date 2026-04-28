import socket
import smtplib
import unittest.mock

import flask
import flask_mail
import pytest

import tests
import http
from dds_web.database import models
from dds_web import db
from dds_web.errors import TwoFactorEmailError
from dds_web.security.auth import send_hotp_email


# verify_token
def test_verify_token_user_not_exists_after_deletion(client):
    """Log in, delete, log out. Should give exception."""
    # Check that user exists
    current_user: models.UnitUser = models.User.query.get("unituser")
    assert current_user

    # Authenticate
    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)

    # Verify that user has access from beginning
    response = client.get(
        tests.DDSEndpoint.LIST_FILES, headers=token, query_string={"project": "public_project_id"}
    )
    assert response.status_code == http.HTTPStatus.OK

    # Delete user
    db.session.delete(current_user)
    db.session.commit()

    # Check that user dot not exist
    current_user: models.UnitUser = models.User.query.get("unituser")
    assert not current_user

    # Attempt run
    response = client.get(tests.DDSEndpoint.LIST_FILES, headers=token)
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # Verify message
    response_json = response.json
    message = response_json.get("message")
    assert message == "Invalid token. Try reauthenticating."


# send_hotp_email -- unit tests for the mail-failure handling ###############
#
# send_hotp_email must convert transient mail-send failures (SMTP / DNS /
# socket layer) into a TwoFactorEmailError. We need an active request
# context because the function inspects flask.request.path.


@pytest.fixture
def request_ctx_for_login(client):
    """Push a request context that looks like a /login POST.

    send_hotp_email branches on flask.request.path and skips sending if the
    path ends in /user/hotp/activate, so we use /login here.
    """
    app = flask.current_app or client.application
    with app.test_request_context("/login", method="POST"):
        yield


def _fresh_user_for_hotp() -> models.User:
    """Return a user whose hotp cooldown has expired so a send is attempted."""
    user = models.User.query.get("researchuser")
    user.hotp_issue_time = None
    db.session.commit()
    return user


@pytest.mark.parametrize(
    "exc",
    [
        socket.gaierror(-3, "Try again"),
        smtplib.SMTPException("relay rejected"),
        TimeoutError("smtp connect timeout"),
        OSError("connection reset by peer"),
    ],
)
def test_send_hotp_email_raises_TwoFactorEmailError_on_mail_failure(
    request_ctx_for_login, exc
):
    """Each of the documented failure modes must surface as TwoFactorEmailError."""
    user = _fresh_user_for_hotp()

    with unittest.mock.patch.object(flask_mail.Mail, "send", side_effect=exc):
        with pytest.raises(TwoFactorEmailError):
            send_hotp_email(user)


def test_send_hotp_email_does_not_raise_on_cooldown(request_ctx_for_login):
    """The cooldown / no-send branch must keep returning False, not raise."""
    user = models.User.query.get("researchuser")
    # Pretend a HOTP was just issued -- send_hotp_email should not call mail.send.
    import datetime
    import dds_web.utils

    user.hotp_issue_time = dds_web.utils.current_time()
    db.session.commit()

    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        result = send_hotp_email(user)
        assert mock_mail_send.call_count == 0

    assert result is False


def test_send_hotp_email_returns_True_on_successful_send(request_ctx_for_login):
    """Happy-path regression: a successful mail.send returns True."""
    user = _fresh_user_for_hotp()

    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        result = send_hotp_email(user)
        assert mock_mail_send.call_count == 1

    assert result is True
