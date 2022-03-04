import http

import tests
import flask


def successful_web_login(client, user_auth):
    response = client.get(tests.DDSEndpoint.LOGIN)
    assert response.status_code == http.HTTPStatus.OK

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
    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.CONFIRM_2FA

    form_token = flask.g.csrf_token

    form_data = {
        "csrf_token": form_token,
        "hotp": user_auth.fetch_hotp().decode(),
        "submit": "Authenticate",
    }

    response = client.post(
        tests.DDSEndpoint.CONFIRM_2FA,
        json=form_data,
        follow_redirects=True,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert flask.request.path == tests.DDSEndpoint.INDEX
    assert flask.request.path == flask.url_for("pages.home")

    return flask.g.csrf_token


def test_load_login_page(client):
    user_auth = tests.UserAuth(tests.USER_CREDENTIALS["researcher"])

    response = client.get(tests.DDSEndpoint.LOGIN)
    assert response.status == "200 OK"


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
