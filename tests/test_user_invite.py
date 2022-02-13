import tests
import flask
from dds_web.database import models
from dds_web.security.project_user_keys import generate_invite_key_pair
from dds_web.security.tokens import encrypted_jwt_token
import datetime


def get_email_token(invite):
    return encrypted_jwt_token(
        username="",
        sensitive_content=generate_invite_key_pair(invite).hex(),
        expires_in=datetime.timedelta(hours=24),
        additional_claims={"inv": invite.email},
    )


def test_no_token(client):
    response = client.get(tests.DDSEndpoint.USER_CONFIRM, content_type="application/json")
    assert response.status == "404 NOT FOUND"


def test_invalid_token(client):
    response = client.get(
        tests.DDSEndpoint.USER_CONFIRM + "invalidtokentesting",
        content_type="application/json",
        follow_redirects=True,
    )

    assert response.status == "200 OK"
    # index redirects to login
    assert flask.request.path == flask.url_for("auth_blueprint.login")


def test_expired_token(client):
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


def test_valid_token(client):
    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()
    assert invite

    token = get_email_token(invite)
    assert token

    response = client.get(tests.DDSEndpoint.USER_CONFIRM + token, content_type="application/json")
    assert response.status == "200 OK"
    assert b"Registration form" in response.data


def test_register_no_form(client):
    response = client.post(tests.DDSEndpoint.USER_NEW, content_type="application/json")
    assert response.status == "400 BAD REQUEST"


def test_register_no_token_in_session(client):
    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()
    assert invite

    token = get_email_token(invite)
    assert token

    response = client.get(tests.DDSEndpoint.USER_CONFIRM + token, content_type="application/json")
    assert response.status == "200 OK"
    assert b"Registration form" in response.data

    form_token = flask.g.csrf_token

    with client.session_transaction() as client_session:
        client_session.pop("invite_token", None)

    form_data = {
        "csrf_token": form_token,
        "email": invite.email,
        "name": "Test User",
        "username": "user_not_existing",
        "password": "Password123",
        "confirm": "Password123",
        "submit": "submit",
    }

    response = client.post(
        tests.DDSEndpoint.USER_NEW,
        json=form_data,
        follow_redirects=True,
    )
    assert response.status == "200 OK"
    assert flask.request.path == tests.DDSEndpoint.LOGIN

    # Invite should be kept and user should not be created
    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()

    assert invite is not None

    user = models.User.query.filter_by(username=form_data["username"]).one_or_none()
    assert user is None


def test_register_weak_password(client):
    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()
    assert invite

    token = get_email_token(invite)
    assert token

    response = client.get(tests.DDSEndpoint.USER_CONFIRM + token, content_type="application/json")
    assert response.status == "200 OK"
    assert b"Registration form" in response.data

    form_token = flask.g.csrf_token

    form_data = {
        "csrf_token": form_token,
        "email": invite.email,
        "name": "Test User",
        "username": "user_not_existing",
        "password": "password",
        "confirm": "password",
        "submit": "submit",
    }

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


def test_successful_register(client):
    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()
    assert invite

    invite_id = invite.id

    token = get_email_token(invite)
    assert token

    response = client.get(tests.DDSEndpoint.USER_CONFIRM + token, content_type="application/json")
    assert response.status == "200 OK"
    assert b"Registration form" in response.data

    form_token = flask.g.csrf_token

    form_data = {
        "csrf_token": form_token,
        "email": invite.email,
        "name": "Test User",
        "username": "user_not_existing",
        "password": "Password123",
        "confirm": "Password123",
        "submit": "submit",
    }

    response = client.post(
        tests.DDSEndpoint.USER_NEW,
        json=form_data,
        follow_redirects=True,
    )
    assert response.status == "200 OK"

    invite = models.Invite.query.filter_by(
        email="existing_invite_email@mailtrap.io", role="Researcher"
    ).one_or_none()

    assert invite is None

    assert len(models.ProjectInviteKeys.query.filter_by(invite_id=invite_id).all()) == 0

    user = models.User.query.filter_by(username=form_data["username"]).one_or_none()
    assert user is not None
    assert user.temporary_key is not None
    assert user.nonce is not None
    assert user.public_key is not None
    assert user.private_key is not None
