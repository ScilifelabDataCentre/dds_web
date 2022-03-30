from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import datetime
import http
import flask
import flask_mail
import pytest
import unittest

import tests
from dds_web import db
from dds_web import utils
from dds_web.database import models
from dds_web.security.project_user_keys import generate_invite_key_pair
from dds_web.security.tokens import encrypted_jwt_token


def test_request_reset_password_no_form(client):
    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.post(
            tests.DDSEndpoint.REQUEST_RESET_PASSWORD, json={}, content_type="application/json"
        )
        assert mock_mail_send.call_count == 0


def test_request_reset_password_nonexisting_email(client):
    response = client.get(tests.DDSEndpoint.REQUEST_RESET_PASSWORD)
    assert response.status_code == http.HTTPStatus.OK
    form_token = flask.g.csrf_token

    form_data = {
        "csrf_token": form_token,
        "email": "incorrect@example.org",
        "submit": "Request Password Reset",
    }
    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.post(
            tests.DDSEndpoint.REQUEST_RESET_PASSWORD,
            json=form_data,
            content_type="application/json",
        )
        assert mock_mail_send.call_count == 0


def test_request_reset_password_inactive_user(client):
    response = client.get(tests.DDSEndpoint.REQUEST_RESET_PASSWORD)
    assert response.status_code == http.HTTPStatus.OK
    form_token = flask.g.csrf_token

    researchuser = models.User.query.filter_by(username="researchuser").first()
    researchuser.active = False
    db.session.add(researchuser)
    db.session.commit()

    db.session.refresh(researchuser)

    form_data = {
        "csrf_token": form_token,
        "email": researchuser.primary_email,
        "submit": "Request Password Reset",
    }
    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.post(
            tests.DDSEndpoint.REQUEST_RESET_PASSWORD,
            json=form_data,
            content_type="application/json",
        )
        assert mock_mail_send.call_count == 0


def test_request_reset_password(client):
    response = client.get(tests.DDSEndpoint.REQUEST_RESET_PASSWORD)
    assert response.status_code == http.HTTPStatus.OK
    form_token = flask.g.csrf_token

    form_data = {
        "csrf_token": form_token,
        "email": "researchuser@mailtrap.io",
        "submit": "Request Password Reset",
    }
    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.post(
            tests.DDSEndpoint.REQUEST_RESET_PASSWORD,
            json=form_data,
            content_type="application/json",
        )
        assert mock_mail_send.call_count == 1


def test_reset_password_no_token(client):
    response = client.get(tests.DDSEndpoint.RESET_PASSWORD, follow_redirects=True)
    # URL with trailing slash is not valid
    assert response.status_code == http.HTTPStatus.NOT_FOUND


def test_reset_password_invalid_token_get(client):
    auth_token_header = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    token = auth_token_header["Authorization"].split(" ")[1]

    response = client.get(tests.DDSEndpoint.RESET_PASSWORD + token, follow_redirects=True)
    # Redirection status code
    assert response.status_code == http.HTTPStatus.OK
    # Incorrect token should redirect and not lead to form
    assert flask.request.path == tests.DDSEndpoint.INDEX


def get_valid_reset_token(username, expires_in=3600):
    return encrypted_jwt_token(
        username=username,
        sensitive_content=None,
        expires_in=datetime.timedelta(
            seconds=expires_in,
        ),
        additional_claims={"rst": "pwd"},
    )


def test_reset_password_invalid_token_post(client):
    nr_proj_user_keys_before = models.ProjectUserKeys.query.count()
    user = models.User.query.filter_by(username="researchuser").first()
    researchuser_pw_hash_before = user._password_hash

    # Add new row to password reset
    new_reset_row = models.PasswordReset(
        user=user, email=user.primary_email, issued=utils.timestamp()
    )
    db.session.add(new_reset_row)
    db.session.commit()

    # Need to use a valid token for the get request to get the form token
    valid_reset_token = get_valid_reset_token("researchuser")
    response = client.get(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, follow_redirects=True
    )

    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token

    form_token = flask.g.csrf_token
    form_data = {
        "csrf_token": form_token,
        "password": "NewPassword123",
        "confirm_password": "NewPassword123",
        "submit": "Reset Password",
    }

    auth_token_header = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    invalid_token = auth_token_header["Authorization"].split(" ")[1]

    response = client.post(
        tests.DDSEndpoint.RESET_PASSWORD + invalid_token, json=form_data, follow_redirects=True
    )
    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.INDEX

    # Just make sure no project user keys has been removed
    nr_proj_user_keys_after = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_before == nr_proj_user_keys_after

    researchuser_pw_hash_after = (
        models.User.query.filter_by(username="researchuser").first()._password_hash
    )
    assert researchuser_pw_hash_before == researchuser_pw_hash_after


def test_reset_password_expired_token_get(client):
    token = get_valid_reset_token("researchuser", expires_in=-1)
    response = client.get(tests.DDSEndpoint.RESET_PASSWORD + token, follow_redirects=True)

    assert response.status_code == http.HTTPStatus.OK
    # Incorrect token should redirect and not lead to form
    assert flask.request.path == tests.DDSEndpoint.INDEX


def test_reset_password_expired_token_post_no_password_reset_row(client):
    nr_proj_user_keys_before = models.ProjectUserKeys.query.count()
    user = models.User.query.filter_by(username="researchuser").first()
    researchuser_pw_hash_before = user._password_hash

    # Need to use a valid token for the get request to get the form token
    valid_reset_token = get_valid_reset_token("researchuser")
    response = client.get(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, follow_redirects=True
    )

    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.INDEX


def test_reset_password_expired_token_post(client):
    nr_proj_user_keys_before = models.ProjectUserKeys.query.count()
    user = models.User.query.filter_by(username="researchuser").first()
    researchuser_pw_hash_before = user._password_hash

    # Add new row to password reset
    new_reset_row = models.PasswordReset(
        user=user, email=user.primary_email, issued=utils.timestamp()
    )
    db.session.add(new_reset_row)
    db.session.commit()

    # Need to use a valid token for the get request to get the form token
    valid_reset_token = get_valid_reset_token("researchuser")
    response = client.get(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, follow_redirects=True
    )

    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token

    form_token = flask.g.csrf_token
    form_data = {
        "csrf_token": form_token,
        "password": "NewPassword123",
        "confirm_password": "NewPassword123",
        "submit": "Reset Password",
    }

    expired_token = get_valid_reset_token("researchuser", expires_in=-1)

    response = client.post(
        tests.DDSEndpoint.RESET_PASSWORD + expired_token, json=form_data, follow_redirects=True
    )
    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.INDEX

    # Just make sure no project user keys has been removed
    nr_proj_user_keys_after = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_before == nr_proj_user_keys_after

    researchuser_pw_hash_after = (
        models.User.query.filter_by(username="researchuser").first()._password_hash
    )
    assert researchuser_pw_hash_before == researchuser_pw_hash_after


def test_reset_password_researchuser_no_password_reset_row(client):
    user = models.User.query.filter_by(username="researchuser").first()
    nr_proj_user_keys_total_before = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_total_before > 0

    nr_proj_user_keys_before = len(user.project_user_keys)
    assert nr_proj_user_keys_before > 0

    user_pw_hash_before = user._password_hash
    user_public_key_before = user.public_key

    # Need to use a valid token for the get request to get the form token
    valid_reset_token = get_valid_reset_token("researchuser")
    response = client.get(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, follow_redirects=True
    )

    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.INDEX


def test_reset_password_researchuser(client):
    user = models.User.query.filter_by(username="researchuser").first()
    nr_proj_user_keys_total_before = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_total_before > 0

    nr_proj_user_keys_before = len(user.project_user_keys)
    assert nr_proj_user_keys_before > 0

    user_pw_hash_before = user._password_hash
    user_public_key_before = user.public_key

    # Add new row to password reset
    new_reset_row = models.PasswordReset(
        user=user, email=user.primary_email, issued=utils.timestamp()
    )
    db.session.add(new_reset_row)
    db.session.commit()

    # Need to use a valid token for the get request to get the form token
    valid_reset_token = get_valid_reset_token("researchuser")
    response = client.get(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, follow_redirects=True
    )

    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token

    form_token = flask.g.csrf_token
    form_data = {
        "csrf_token": form_token,
        "password": "NewPassword123",
        "confirm_password": "NewPassword123",
        "submit": "Reset Password",
    }

    response = client.post(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, json=form_data, follow_redirects=True
    )
    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.PASSWORD_RESET_COMPLETED

    user = models.User.query.filter_by(username="researchuser").first()

    # All users project keys should have been removed
    nr_proj_user_keys_after = len(user.project_user_keys)
    assert nr_proj_user_keys_after == 0

    # Total nr of project user keys should be decreased
    nr_proj_user_keys_total_after = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_total_after < nr_proj_user_keys_total_before
    assert nr_proj_user_keys_total_after != nr_proj_user_keys_total_before

    # Password should have changed
    user_pw_hash_after = user._password_hash
    assert user_pw_hash_before != user_pw_hash_after

    # Check that public key has changed
    user_public_key_after = user.public_key
    assert user_public_key_before != user_public_key_after


def test_reset_password_project_owner_no_password_reset_row(client):
    user = models.User.query.filter_by(username="projectowner").first()
    nr_proj_user_keys_total_before = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_total_before > 0

    nr_proj_user_keys_before = len(user.project_user_keys)
    assert nr_proj_user_keys_before > 0

    user_pw_hash_before = user._password_hash
    user_public_key_before = user.public_key

    # Need to use a valid token for the get request to get the form token
    valid_reset_token = get_valid_reset_token("projectowner")
    response = client.get(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, follow_redirects=True
    )

    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.INDEX


def test_reset_password_project_owner(client):
    user = models.User.query.filter_by(username="projectowner").first()
    nr_proj_user_keys_total_before = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_total_before > 0

    nr_proj_user_keys_before = len(user.project_user_keys)
    assert nr_proj_user_keys_before > 0

    user_pw_hash_before = user._password_hash
    user_public_key_before = user.public_key

    # Add new row to password reset
    new_reset_row = models.PasswordReset(
        user=user, email=user.primary_email, issued=utils.timestamp()
    )
    db.session.add(new_reset_row)
    db.session.commit()

    # Need to use a valid token for the get request to get the form token
    valid_reset_token = get_valid_reset_token("projectowner")
    response = client.get(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, follow_redirects=True
    )

    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token

    form_token = flask.g.csrf_token
    form_data = {
        "csrf_token": form_token,
        "password": "NewPassword123",
        "confirm_password": "NewPassword123",
        "submit": "Reset Password",
    }

    response = client.post(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, json=form_data, follow_redirects=True
    )
    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.PASSWORD_RESET_COMPLETED

    user = models.User.query.filter_by(username="projectowner").first()

    # All users project keys should have been removed
    nr_proj_user_keys_after = len(user.project_user_keys)
    assert nr_proj_user_keys_after == 0

    # Total nr of project user keys should be decreased
    nr_proj_user_keys_total_after = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_total_after < nr_proj_user_keys_total_before
    assert nr_proj_user_keys_total_after != nr_proj_user_keys_total_before

    # Password should have changed
    user_pw_hash_after = user._password_hash
    assert user_pw_hash_before != user_pw_hash_after

    # Check that public key has changed
    user_public_key_after = user.public_key
    assert user_public_key_before != user_public_key_after


def test_reset_password_unituser_no_password_reset_row(client):
    user = models.User.query.filter_by(username="unituser").first()
    nr_proj_user_keys_total_before = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_total_before > 0

    nr_proj_user_keys_before = len(user.project_user_keys)
    assert nr_proj_user_keys_before > 0

    user_pw_hash_before = user._password_hash
    user_public_key_before = user.public_key

    # Need to use a valid token for the get request to get the form token
    valid_reset_token = get_valid_reset_token("unituser")
    response = client.get(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, follow_redirects=True
    )

    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.INDEX


def test_reset_password_unituser(client):
    user = models.User.query.filter_by(username="unituser").first()
    nr_proj_user_keys_total_before = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_total_before > 0

    nr_proj_user_keys_before = len(user.project_user_keys)
    assert nr_proj_user_keys_before > 0

    user_pw_hash_before = user._password_hash
    user_public_key_before = user.public_key

    # Add new row to password reset
    new_reset_row = models.PasswordReset(
        user=user, email=user.primary_email, issued=utils.timestamp()
    )
    db.session.add(new_reset_row)
    db.session.commit()

    # Need to use a valid token for the get request to get the form token
    valid_reset_token = get_valid_reset_token("unituser")
    response = client.get(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, follow_redirects=True
    )

    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token

    form_token = flask.g.csrf_token
    form_data = {
        "csrf_token": form_token,
        "password": "NewPassword123",
        "confirm_password": "NewPassword123",
        "submit": "Reset Password",
    }

    response = client.post(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, json=form_data, follow_redirects=True
    )
    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.PASSWORD_RESET_COMPLETED

    user = models.User.query.filter_by(username="unituser").first()

    # All users project keys should have been removed
    nr_proj_user_keys_after = len(user.project_user_keys)
    assert nr_proj_user_keys_after == 0

    # Total nr of project user keys should be decreased
    nr_proj_user_keys_total_after = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_total_after < nr_proj_user_keys_total_before
    assert nr_proj_user_keys_total_after != nr_proj_user_keys_total_before

    # Password should have changed
    user_pw_hash_after = user._password_hash
    assert user_pw_hash_before != user_pw_hash_after

    # Check that public key has changed
    user_public_key_after = user.public_key
    assert user_public_key_before != user_public_key_after


def test_reset_password_unitadmin(client):
    user = models.User.query.filter_by(username="unitadmin").first()
    nr_proj_user_keys_total_before = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_total_before > 0

    nr_proj_user_keys_before = len(user.project_user_keys)
    assert nr_proj_user_keys_before > 0

    user_pw_hash_before = user._password_hash
    user_public_key_before = user.public_key

    # Add new row to password reset
    new_reset_row = models.PasswordReset(
        user=user, email=user.primary_email, issued=utils.timestamp()
    )
    db.session.add(new_reset_row)
    db.session.commit()

    # Need to use a valid token for the get request to get the form token
    valid_reset_token = get_valid_reset_token("unitadmin")
    response = client.get(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, follow_redirects=True
    )

    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token

    form_token = flask.g.csrf_token
    form_data = {
        "csrf_token": form_token,
        "password": "NewPassword123",
        "confirm_password": "NewPassword123",
        "submit": "Reset Password",
    }

    response = client.post(
        tests.DDSEndpoint.RESET_PASSWORD + valid_reset_token, json=form_data, follow_redirects=True
    )
    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.PASSWORD_RESET_COMPLETED

    user = models.User.query.filter_by(username="unitadmin").first()

    # All users project keys should have been removed
    nr_proj_user_keys_after = len(user.project_user_keys)
    assert nr_proj_user_keys_after == 0

    # Total nr of project user keys should be decreased
    nr_proj_user_keys_total_after = models.ProjectUserKeys.query.count()
    assert nr_proj_user_keys_total_after < nr_proj_user_keys_total_before
    assert nr_proj_user_keys_total_after != nr_proj_user_keys_total_before

    # Password should have changed
    user_pw_hash_after = user._password_hash
    assert user_pw_hash_before != user_pw_hash_after

    # Check that public key has changed
    user_public_key_after = user.public_key
    assert user_public_key_before != user_public_key_after
