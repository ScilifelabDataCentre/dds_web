import datetime
import flask
from http import HTTPStatus

from tests import UserAuth, USER_CREDENTIALS, DDSEndpoint

from dds_web.security.tokens import encrypted_jwt_token


def successful_web_login(client: flask.testing.FlaskClient, user_auth: UserAuth):
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.LOGIN)
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
    )
    assert response.status_code == HTTPStatus.OK
    assert flask.request.path == DDSEndpoint.CONFIRM_2FA

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
    )
    assert response.status_code == HTTPStatus.OK
    assert flask.request.path == DDSEndpoint.INDEX
    assert flask.request.path == flask.url_for("pages.home")

    return form_token


def test_load_login_page(client: flask.testing.FlaskClient):
    user_auth: UserAuth = UserAuth(USER_CREDENTIALS["researcher"])

    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.LOGIN)
    assert response.status_code == HTTPStatus.OK


def test_cancel_2fa(client: flask.testing.FlaskClient):
    user_auth = UserAuth(USER_CREDENTIALS["researcher"])

    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.LOGIN)
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
    )
    assert response.status_code == HTTPStatus.OK
    assert flask.request.path == DDSEndpoint.CONFIRM_2FA

    second_factor_token: str = flask.session.get("2fa_initiated_token")
    assert second_factor_token is not None

    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.CANCEL_2FA,
        follow_redirects=True,
    )

    assert response.status_code == HTTPStatus.OK
    assert flask.request.path == DDSEndpoint.LOGIN

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
        DDSEndpoint.USER_INFO, headers=headers, follow_redirects=True
    )
    assert response.status_code == HTTPStatus.OK
    assert flask.request.path == DDSEndpoint.USER_INFO

    form_token: str = flask.g.csrf_token

    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.LOGOUT,
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.OK
    assert flask.request.path == DDSEndpoint.INDEX

    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.REQUEST_RESET_PASSWORD,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "csrf_token": form_token,
            "email": "researchuser@mailtrap.io",
        },
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.content_type == "text/html; charset=utf-8"
    assert flask.request.path == DDSEndpoint.LOGIN

    response: werkzeug.test.WrapperTestResponse = client.post(
        f"{DDSEndpoint.REQUEST_RESET_PASSWORD}/{token}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "csrf_token": form_token,
            "password": "Password1!",
            "confirm_password": "Password1!",
        },
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.content_type == "text/html; charset=utf-8"
    assert flask.request.path == DDSEndpoint.PASSWORD_RESET_COMPLETED

    with client.session_transaction() as session:
        session["reset_token"] = token

    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PASSWORD_RESET_COMPLETED,
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.content_type == "text/html; charset=utf-8"
    assert flask.request.path == DDSEndpoint.PASSWORD_RESET_COMPLETED

    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.USER_INFO,
        headers=headers,
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.content_type == "application/json"
    assert flask.request.path == DDSEndpoint.USER_INFO
    assert (
        response.json.get("message")
        == "Password reset performed after last authentication. Start a new authenticated session to proceed."
    )
