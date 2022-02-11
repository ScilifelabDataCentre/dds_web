import tests
import flask
from dds_web import db
from dds_web.database import models
import dds_web.errors as ddserr
from dds_web.security.tokens import encrypted_jwt_token
import datetime


def test_cancel_2fa(client):
    user_auth = tests.UserAuth(tests.USER_CREDENTIALS["researcher"])

    response = client.get(tests.DDSEndpoint.LOGIN)
    assert response.status == "200 OK"

    form_token = flask.g.csrf_token

    form_data = {
        "csrf_token": form_token,
        "username": user_auth.as_tuple()[0],
        "password": user_auth.as_tuple()[1],
        "submit": "Login",
    }

    response = client.post(
        tests.DDSEndpoint.LOGIN,
        json=form_data,
        follow_redirects=True,
    )
    assert response.status == "200 OK"
    assert flask.request.path == tests.DDSEndpoint.CONFIRM_2FA

    second_factor_token = flask.session.get("2fa_initiated_token")
    assert second_factor_token is not None

    response = client.post(
        tests.DDSEndpoint.CANCEL_2FA,
        follow_redirects=True,
    )

    assert response.status == "200 OK"
    assert flask.request.path == tests.DDSEndpoint.LOGIN

    second_factor_token = flask.session.get("2fa_initiated_token")
    assert second_factor_token is None
