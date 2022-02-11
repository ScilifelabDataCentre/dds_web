import tests
import flask
import pytest
from dds_web import db
from dds_web.database import models
import dds_web.errors as ddserr
from dds_web.security.tokens import encrypted_jwt_token
import datetime


def get_email_token(email):
    return encrypted_jwt_token(
        username="",
        sensitive_content="BOGUS",
        expires_in=datetime.timedelta(hours=24),
        additional_claims={"inv": email},
    )


def test_confirm_invite_no_token(client):
    response = client.get(tests.DDSEndpoint.USER_CONFIRM, content_type="application/json")
    assert response.status == "404 NOT FOUND"


def test_confirm_invite_invalid_token(client):
    response = client.get(
        tests.DDSEndpoint.USER_CONFIRM + "invalidtokentesting",
        content_type="application/json",
        follow_redirects=True,
    )

    assert response.status == "200 OK"
    # index redirects to login
    assert flask.request.path == flask.url_for("auth_blueprint.login")


def test_confirm_invite_expired_token(client):
    response = client.get(
        tests.DDSEndpoint.USER_CONFIRM
        + (
            "eyJhbGciOiJBMjU2S1ciLCJlbmMiOiJBMjU2R0NNIn0.BQvaqAvJHN_2LooUP3oOa_CFOwkrT1cQefXC"
            "awOlNhD6Y3g-Nn2jyg.PiQs3nSPC-4sWd2D.m0crUKeQNlOFbhybHkXBZx_Akv1H41NyMcyem0p2yWTq"
            "Ksgxta9k-S0wMWWvFd0Bogq71YvHocH8llVyPCm4ZfrvpiJFH0JslkcfSxFuwVMb-rFWK32PJFV2edbM"
            "FsirbsJblbNT59rdE24BP07yrGwJlUxL9tLgfcpqidLG5vPsBaDYPQ3WniUUDJE7ymj0eZ23a3FOXCWY"
            "QG7sZB5fJlnDgHQtjjeT8_22DF811wxqS4QEmn4LH_fv7RPpOwAFIeuERuQ6OTodZfgYVxS1ghbmFvAo"
            "Vh7u7-tpVzH-W9cGh4rAnNPd1wjIaUDnMBbSwP8cm0pjPOKrG0t8LyTbTzTXTd3kpLLd6DbmPe_EE5lB"
            "tKEh6slu_4TMi5LrtlGUdUby.Ughc9A6ZHFXjR9i_FSSQBg"
        ),
        content_type="application/json",
        follow_redirects=True,
    )
    assert response.status == "200 OK"
    # index redirects to login
    assert flask.request.path == flask.url_for("auth_blueprint.login")


def test_confirm_invite_valid_token(client):
    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()
    assert invite

    token = get_email_token(email=invite.email)
    assert token

    response = client.get(tests.DDSEndpoint.USER_CONFIRM + token, content_type="application/json")
    assert response.status == "200 OK"
    assert b"Registration form" in response.data


def test_register_no_form(client):
    response = client.post(tests.DDSEndpoint.USER_NEW, content_type="application/json")
    assert response.status == "400 BAD REQUEST"


@pytest.fixture()
def registry_form_data(client):
    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()
    assert invite
    assert invite.public_key

    token = get_email_token(email=invite.email)
    assert token

    response = client.get(tests.DDSEndpoint.USER_CONFIRM + token, content_type="application/json")
    assert response.status == "200 OK"
    assert b"Registration form" in response.data

    form_token = flask.g.csrf_token

    return {
        "csrf_token": form_token,
        "email": invite.email,
        "name": "Test User",
        "username": "user_not_existing",
        "password": "Password123",
        "confirm": "Password123",
        "submit": "submit",
    }


def test_register_no_token_in_session(registry_form_data, client):
    with client.session_transaction() as client_session:
        client_session.pop("invite_token", None)

    response = client.post(
        tests.DDSEndpoint.USER_NEW,
        json=registry_form_data,
        follow_redirects=True,
    )
    assert response.status == "200 OK"
    assert flask.request.path == tests.DDSEndpoint.LOGIN

    # Invite should be kept and user should not be created
    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()

    assert invite is not None

    user = models.User.query.filter_by(username=registry_form_data["username"]).one_or_none()
    assert user is None


def test_register_weak_password(registry_form_data, client):
    form_data = registry_form_data
    form_data["password"] = "password"
    form_data["confirm"] = "password"

    response = client.post(
        tests.DDSEndpoint.USER_NEW,
        json=form_data,
        follow_redirects=True,
    )
    assert response.status == "200 OK"
    assert flask.request.path == tests.DDSEndpoint.USER_NEW

    # Invite should be kept and user should not be created
    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()

    assert invite is not None

    user = models.User.query.filter_by(username=form_data["username"]).one_or_none()
    assert user is None


def test_successful_registration(registry_form_data, client):
    response = client.post(
        tests.DDSEndpoint.USER_NEW,
        json=registry_form_data,
        follow_redirects=True,
    )
    assert response.status == "200 OK"

    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()

    assert invite is None

    user = models.User.query.filter_by(username=registry_form_data["username"]).one_or_none()
    assert user is not None


def test_successful_registration_should_transfer_keys(registry_form_data, client):
    invite = models.Invite.query.filter_by(
        email=registry_form_data["email"], role="Researcher"
    ).one_or_none()

    invite_encrypted_private_key = invite.private_key
    invite_public_key = invite.public_key

    assert invite_encrypted_private_key
    assert invite_public_key

    response = client.post(
        tests.DDSEndpoint.USER_NEW,
        json=registry_form_data,
        follow_redirects=True,
    )
    assert response.status == "200 OK"

    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()

    assert invite is None

    user = models.User.query.filter_by(username=registry_form_data["username"]).one_or_none()
    assert user is not None

    assert user.public_key == invite_public_key
    # Encryption should have changed the stored value
    assert user.private_key != invite_encrypted_private_key
