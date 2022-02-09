import json
import tests
import flask
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

    token = get_email_token(email=invite.email)
    assert token

    response = client.get(tests.DDSEndpoint.USER_CONFIRM + token, content_type="application/json")
    assert response.status == "200 OK"
    assert b"Registration form" in response.data
