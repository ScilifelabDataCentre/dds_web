# Standard libraries
import http

# Installed
import json

# Own
import tests

user = {"email": "researchuser2@mailtrap.io", "username": "researchuser2", "role": "Researcher"}
unituser = {"email": "unituser1@mailtrap.io", "username": "unituser", "role": "Unit Personnel"}


def test_deactivate_self_as_superadmin(module_client):
    """Deactivate self as superadmin"""
    response = module_client.post(
        tests.DDSEndpoint.USER_ACTIVATION,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(module_client),
        data=json.dumps({"email": "superadmin@mailtrap.io", "action": "deactivate"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert f"You cannot deactivate your own account!" in response.json["message"]


def test_deactivate_nouser_as_superadmin(module_client):
    """Deactivate nonexistent user as superadmin"""
    response = module_client.post(
        tests.DDSEndpoint.USER_ACTIVATION,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(module_client),
        data=json.dumps({"email": "nossuchemail@mailtrap.io", "action": "deactivate"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert (
        f"This e-mail address is not associated with a user in the DDS, make sure it is not misspelled."
        in response.json["message"]
    )


def test_deactivate_user_as_superadmin(module_client):
    """Deactivate researchuser as super admin"""
    # Try to get token as user that is to be deactivated
    response = module_client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS[user["username"]]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.OK

    # Deactivate user
    response = module_client.post(
        tests.DDSEndpoint.USER_ACTIVATION,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(module_client),
        data=json.dumps({**user, "action": "deactivate"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert (
        f"You successfully deactivated the account {user['username']} ({user['email']}, {user['role']})!"
        in response.json["message"]
    )

    # Try to get token after deactivation
    response = module_client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS[user["username"]]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED


def test_deactivate_deactivated_user_as_superadmin(module_client):
    """Deactivate deactivated researchuser as super admin"""
    # Deactivate user again
    response = module_client.post(
        tests.DDSEndpoint.USER_ACTIVATION,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(module_client),
        data=json.dumps({**user, "action": "deactivate"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "User is already in desired state!" in response.json["message"]


def test_reactivate_user_as_superadmin(module_client):
    """Reactivate researchuser as super admin"""
    # Try to get token as user that is to be deactivated
    response = module_client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS[user["username"]]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED

    # Reactivate user
    response = module_client.post(
        tests.DDSEndpoint.USER_ACTIVATION,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(module_client),
        data=json.dumps({**user, "action": "reactivate"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert (
        f"You successfully reactivated the account {user['username']} ({user['email']}, {user['role']})!"
        in response.json["message"]
    )

    # Try to get token after reactivation
    response = module_client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS[user["username"]]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.OK


def test_deactivate_user_as_unitadmin(module_client):
    """Deactivate researchuser as unit admin"""
    # Try to get token as user that is to be deactivated
    response = module_client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS[user["username"]]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.OK

    # Deactivate user
    response = module_client.post(
        tests.DDSEndpoint.USER_ACTIVATION,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        data=json.dumps({**user, "action": "deactivate"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert (
        "You are not allowed to deactivate this user. As a unit admin, you're only allowed to deactivate users in your unit."
        in response.json["message"]
    )


def test_deactivate_unituser_as_unitadmin(module_client):
    """Deactivate unit user as unit admin"""
    # Try to get token as user that is to be deactivated
    response = module_client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS[unituser["username"]]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.OK

    # Try without action
    response = module_client.post(
        tests.DDSEndpoint.USER_ACTIVATION,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        data=json.dumps({**unituser}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert (
        "Please provide an action 'deactivate' or 'reactivate' for this request."
        in response.json["message"]
    )

    # Deactivate user
    response = module_client.post(
        tests.DDSEndpoint.USER_ACTIVATION,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        data=json.dumps({**unituser, "action": "deactivate"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert (
        f"You successfully deactivated the account {unituser['username']} ({unituser['email']}, {unituser['role']})!"
        in response.json["message"]
    )

    # Try to get token after deactivation
    response = module_client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS[unituser["username"]]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED


def test_reactivate_unituser_as_unitadmin(module_client):
    """Reactivate unituser as unit admin"""
    # Try to get token as user that is to be deactivated
    response = module_client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS[unituser["username"]]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED

    # Reactivate user
    response = module_client.post(
        tests.DDSEndpoint.USER_ACTIVATION,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(module_client),
        data=json.dumps({**unituser, "action": "reactivate"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert (
        f"You successfully reactivated the account {unituser['username']} ({unituser['email']}, {unituser['role']})!"
        in response.json["message"]
    )

    # Try to get token after reactivation
    response = module_client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS[unituser["username"]]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.OK


def test_deactivate_user_as_unituser(module_client):
    """Deactivate researchuser as unit user"""
    # Try to get token as user that is to be deactivated
    response = module_client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS[user["username"]]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.OK

    # Deactivate user
    response = module_client.post(
        tests.DDSEndpoint.USER_ACTIVATION,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(module_client),
        data=json.dumps({**user, "action": "deactivate"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "Insufficient credentials" in response.json["message"]


def test_deactivate_user_as_researchuser(module_client):
    """Deactivate researchuser as researchuser"""
    # Try to get token as user that is to be deactivated
    response = module_client.get(
        tests.DDSEndpoint.ENCRYPTED_TOKEN,
        auth=tests.UserAuth(tests.USER_CREDENTIALS[user["username"]]).as_tuple(),
    )
    assert response.status_code == http.HTTPStatus.OK

    # Deactivate user
    response = module_client.post(
        tests.DDSEndpoint.USER_ACTIVATION,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(module_client),
        data=json.dumps({**user, "action": "deactivate"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "Insufficient credentials" in response.json["message"]
