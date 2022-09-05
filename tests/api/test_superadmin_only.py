####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import http
import time
import typing

# Installed
import flask
import werkzeug

# Own
from dds_web.database import models
import tests

####################################################################################################
# CONFIG ################################################################################## CONFIG #
####################################################################################################

users: typing.Dict = {
    "Researcher": "researchuser",
    "Unit Personnel": "unituser",
    "Unit Admin": "unitadmin",
    "Super Admin": "superadmin",
}

####################################################################################################
# TESTS #################################################################################### TESTS #
####################################################################################################

# Tools ############################################################################################
def get_token(username: str, client: flask.testing.FlaskClient) -> typing.Dict:
    return tests.UserAuth(tests.USER_CREDENTIALS[username]).token(client)


# AllUnits #########################################################################################


def test_list_units_as_not_superadmin(client: flask.testing.FlaskClient) -> None:
    """Only Super Admin can list users."""
    no_access_users: typing.Dict = users.copy()
    no_access_users.pop("Super Admin")

    for u in no_access_users:
        token: typing.Dict = get_token(username=users[u], client=client)
        response: werkzeug.test.WrapperTestResponse = client.get(
            tests.DDSEndpoint.LIST_UNITS_ALL, headers=token
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_list_units_as_super_admin(client: flask.testing.FlaskClient) -> None:
    """List units as Super Admin."""
    all_units: typing.List = models.Unit.query.all()

    token: typing.Dict = get_token(username=users["Super Admin"], client=client)
    response: werkzeug.test.WrapperTestResponse = client.get(
        tests.DDSEndpoint.LIST_UNITS_ALL, headers=token
    )
    assert response.status_code == http.HTTPStatus.OK

    keys: typing.List = response.json.get("keys")
    units: typing.List = response.json.get("units")
    assert keys and units

    assert keys == [
        "Name",
        "Public ID",
        "External Display Name",
        "Days In Available",
        "Days In Expired",
        "Safespring Endpoint",
        "Contact Email",
        "Size",
    ]
    assert len(all_units) == len(units)

    for unit in all_units:
        expected: typing.Dict = {
            "Name": unit.name,
            "Public ID": unit.public_id,
            "External Display Name": unit.external_display_name,
            "Contact Email": unit.contact_email,
            "Safespring Endpoint": unit.safespring_endpoint,
            "Days In Available": unit.days_in_available,
            "Days In Expired": unit.days_in_expired,
            "Size": unit.size,
        }
        assert expected in units


# MOTD #############################################################################################


def test_create_motd_not_superadmin(client: flask.testing.FlaskClient) -> None:
    """Create a new message of the day, using everything but Super Admin access."""
    no_access_users: typing.Dict = users.copy()
    no_access_users.pop("Super Admin")

    for u in no_access_users:
        token: typing.Dict = get_token(username=users[u], client=client)
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.MOTD, headers=token
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_create_motd_as_superadmin_no_json(client: flask.testing.FlaskClient) -> None:
    """Create a new message of the day, using a Super Admin account, but without any json."""
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)
    response: werkzeug.test.WrapperTestResponse = client.post(tests.DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing from request!" in response.json.get("message")


def test_create_motd_as_superadmin_no_message(client: flask.testing.FlaskClient) -> None:
    """Create a new message of the day, using a Super Admin account, but without any message."""
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)
    response: werkzeug.test.WrapperTestResponse = client.post(
        tests.DDSEndpoint.MOTD, headers=token, json={"test": "test"}
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "No MOTD specified." in response.json.get("message")


def test_create_motd_as_superadmin_empty_message(client: flask.testing.FlaskClient) -> None:
    """Create a new message of the day, using a Super Admin account, but with empty message."""
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)
    response: werkzeug.test.WrapperTestResponse = client.post(
        tests.DDSEndpoint.MOTD, headers=token, json={"message": ""}
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "No MOTD specified." in response.json.get("message")


def test_create_motd_as_superadmin_success(client: flask.testing.FlaskClient) -> None:
    """Create a new message of the day, using a Super Admin account."""
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)
    response: werkzeug.test.WrapperTestResponse = client.post(
        tests.DDSEndpoint.MOTD, headers=token, json={"message": "test"}
    )
    assert response.status_code == http.HTTPStatus.OK
    assert "The MOTD was successfully added to the database." in response.json.get("message")

    assert models.MOTD.query.filter_by(message="test")


def test_get_motd_no_message(client: flask.testing.FlaskClient) -> None:
    """Get latest MOTD from database."""
    response: werkzeug.test.WrapperTestResponse = client.get(
        tests.DDSEndpoint.MOTD, headers=tests.DEFAULT_HEADER
    )
    assert response.status_code == http.HTTPStatus.OK
    assert "There are no active MOTDs." in response.json.get("message")


def test_get_motd(client: flask.testing.FlaskClient) -> None:
    """Get latest MOTD from database."""
    # Create first message
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)
    response: werkzeug.test.WrapperTestResponse = client.post(
        tests.DDSEndpoint.MOTD, headers=token, json={"message": "test"}
    )
    assert response.status_code == http.HTTPStatus.OK
    assert models.MOTD.query.filter_by(message="test")

    # Get first message
    response1: werkzeug.test.WrapperTestResponse = client.get(
        tests.DDSEndpoint.MOTD, headers=tests.DEFAULT_HEADER
    )
    assert response1.status_code == http.HTTPStatus.OK
    assert isinstance(response1.json.get("motds"), list)
    assert "test" in response1.json.get("motds")[0]["Message"]

    time.sleep(5)

    # Create new message
    response2: werkzeug.test.WrapperTestResponse = client.post(
        tests.DDSEndpoint.MOTD, headers=token, json={"message": "something else"}
    )
    assert response2.status_code == http.HTTPStatus.OK
    assert models.MOTD.query.filter_by(message="something else")

    # Check that new message is displayed
    response3: werkzeug.test.WrapperTestResponse = client.get(
        tests.DDSEndpoint.MOTD, headers=tests.DEFAULT_HEADER
    )
    assert response3.status_code == http.HTTPStatus.OK
    assert "something else" in response3.json.get("motds")[1]["Message"]

    # Deactivate message
    response4: werkzeug.test.WrapperTestResponse = client.put(
        tests.DDSEndpoint.MOTD, headers=token, json={"motd_id": 1}
    )
    assert response4.status_code == http.HTTPStatus.OK
    assert "The MOTD was successfully deactivated in the database." in response4.json.get("message")

    # Deactivate message that is not active
    response5: werkzeug.test.WrapperTestResponse = client.put(
        tests.DDSEndpoint.MOTD, headers=token, json={"motd_id": 1}
    )
    assert response5.status_code == http.HTTPStatus.BAD_REQUEST
    assert "MOTD with id 1 is not active." in response5.json.get("message")


def test_deactivate_motd_no_json(client: flask.testing.FlaskClient) -> None:
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)
    response: werkzeug.test.WrapperTestResponse = client.put(tests.DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing from request!" in response.json.get("message")


def test_deactivate_motd_no_motd_id(client: flask.testing.FlaskClient) -> None:
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)
    response: werkzeug.test.WrapperTestResponse = client.put(
        tests.DDSEndpoint.MOTD, headers=token, json={"test": "test"}
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "No MOTD for deactivation specified." in response.json.get("message")


def test_deactivate_motd_no_such_motd(client: flask.testing.FlaskClient) -> None:
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)
    response: werkzeug.test.WrapperTestResponse = client.put(
        tests.DDSEndpoint.MOTD, headers=token, json={"motd_id": 8}
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "MOTD with id 8 does not exist in the database" in response.json.get("message")


def test_deactivate_motd_not_superadmin(client: flask.testing.FlaskClient) -> None:
    """Deactivate a message of the day, using everything but Super Admin access."""
    no_access_users: typing.Dict = users.copy()
    no_access_users.pop("Super Admin")

    for u in no_access_users:
        token: typing.Dict = get_token(username=users[u], client=client)
        response: werkzeug.test.WrapperTestResponse = client.put(
            tests.DDSEndpoint.MOTD, headers=token
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN


# FindUser #########################################################################################


def test_find_user_not_superadmin(client: flask.testing.FlaskClient) -> None:
    """Try finding a specific user without being Super Admin."""
    no_access_users: typing.Dict = users.copy()
    no_access_users.pop("Super Admin")

    for u in no_access_users:
        token: typing.Dict = get_token(username=users[u], client=client)
        response: werkzeug.test.WrapperTestResponse = client.get(
            tests.DDSEndpoint.USER_FIND, headers=token
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_find_user_no_json(client: flask.testing.FlaskClient) -> None:
    """Try finding a specific user without specifying the user."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Get user
    response: werkzeug.test.WrapperTestResponse = client.get(
        tests.DDSEndpoint.USER_FIND, headers=token
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing from request!" in response.json.get("message")


def test_find_user_no_username(client: flask.testing.FlaskClient) -> None:
    """Find specific user with empty username."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Get user
    for x in ["", None]:
        response: werkzeug.test.WrapperTestResponse = client.get(
            tests.DDSEndpoint.USER_FIND, headers=token, json={"username": x}
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Username required to check existence of account." in response.json.get("message")


def test_find_user_non_existent(client: flask.testing.FlaskClient) -> None:
    """Try to find non existent user."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Non existent user
    username: str = "nonexistentuser"
    assert not models.User.query.filter_by(username=username).first()

    # Get user
    response: werkzeug.test.WrapperTestResponse = client.get(
        tests.DDSEndpoint.USER_FIND, headers=token, json={"username": username}
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json and response.json.get("exists") is False


def test_find_user(client: flask.testing.FlaskClient) -> None:
    """Find existing user."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Non existent user
    user_row: models.User = models.User.query.first()
    assert user_row

    # Get user
    response: werkzeug.test.WrapperTestResponse = client.get(
        tests.DDSEndpoint.USER_FIND, headers=token, json={"username": user_row.username}
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json and response.json.get("exists") is True


# ResetTwoFactor ###################################################################################


def test_reset_hotp_not_superadmin(client: flask.testing.FlaskClient) -> None:
    """Try resetting a users HOTP without being Super Admin."""
    no_access_users: typing.Dict = users.copy()
    no_access_users.pop("Super Admin")

    for u in no_access_users:
        token: typing.Dict = get_token(username=users[u], client=client)
        response: werkzeug.test.WrapperTestResponse = client.put(
            tests.DDSEndpoint.TOTP_DEACTIVATE, headers=token
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_reset_hotp_no_json(client: flask.testing.FlaskClient) -> None:
    """Try reseting user HOTP without specifying the user."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Deactivate TOTP
    response: werkzeug.test.WrapperTestResponse = client.put(
        tests.DDSEndpoint.TOTP_DEACTIVATE, headers=token
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing from request!" in response.json.get("message")


def test_reset_hotp_no_username(client: flask.testing.FlaskClient) -> None:
    """Reset users HOTP with empty username."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Deactivate TOTP
    for x in ["", None]:
        response: werkzeug.test.WrapperTestResponse = client.put(
            tests.DDSEndpoint.TOTP_DEACTIVATE, headers=token, json={"username": x}
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Username required to reset 2FA to HOTP" in response.json.get("message")


def test_reset_hotp_non_existent_user(client: flask.testing.FlaskClient) -> None:
    """Try to reset HOTP for non existent user."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Non existent user
    username: str = "nonexistentuser"
    assert not models.User.query.filter_by(username=username).first()

    # Deactivate TOTP
    response: werkzeug.test.WrapperTestResponse = client.put(
        tests.DDSEndpoint.TOTP_DEACTIVATE, headers=token, json={"username": username}
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert f"The user doesn't exist: {username}" in response.json.get("message")


def test_reset_hotp_already_set(client: flask.testing.FlaskClient) -> None:
    """Reset hotp when already set."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Existent user
    user_row: models.User = models.User.query.first()
    assert user_row
    assert not user_row.totp_enabled

    # Deactivate TOTP
    response: werkzeug.test.WrapperTestResponse = client.put(
        tests.DDSEndpoint.TOTP_DEACTIVATE, headers=token, json={"username": user_row.username}
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "TOTP is already deactivated for this user" in response.json.get("message")


def test_reset_hotp(client: flask.testing.FlaskClient) -> None:
    """Reset HOTP."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Existent user
    user_row: models.User = models.User.query.first()
    assert user_row
    user_row.activate_totp()
    assert user_row.totp_enabled

    # Deactivate TOTP
    response: werkzeug.test.WrapperTestResponse = client.put(
        tests.DDSEndpoint.TOTP_DEACTIVATE, headers=token, json={"username": user_row.username}
    )
    assert response.status_code == http.HTTPStatus.OK
    assert (
        f"TOTP has been deactivated for user: {user_row.username}. They can now use 2FA via email during authentication."
        in response.json.get("message")
    )

    user_row_again: models.User = models.User.query.filter_by(username=user_row.username).first()
    assert user_row_again and not user_row_again.totp_enabled
