####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import http
import time
import typing
import unittest
from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import patch
from unittest.mock import PropertyMock

# Installed
import flask
import werkzeug
import flask_mail
import freezegun
import click

# Own
from dds_web import db, mail
from dds_web.database import models
import tests.tests_v3 as tests
from dds_web.commands import collect_stats

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
            "Safespring Endpoint": unit.sto2_endpoint,
            "Days In Available": unit.days_in_available,
            "Days In Expired": unit.days_in_expired,
            "Size": unit.size,
        }

        correct_size: int = 0
        for project in unit.projects:
            for file in project.files:
                correct_size += file.size_stored
        assert correct_size == unit.size
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


def test_find_user_no_username(client: flask.testing.FlaskClient) -> None:
    """Find specific user with empty username."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Get user
    for x in ["", None]:
        response: werkzeug.test.WrapperTestResponse = client.get(
            tests.DDSEndpoint.USER_FIND, headers=token, query_string={"username": ""}
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
        tests.DDSEndpoint.USER_FIND, headers=token, query_string={"username": username}
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
        tests.DDSEndpoint.USER_FIND, headers=token, query_string={"username": user_row.username}
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


# SendMOTD #########################################################################################


def test_send_motd_incorrect_method(client: flask.testing.FlaskClient) -> None:
    """Only post should be accepted."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Attempt request
    with unittest.mock.patch.object(flask_mail.Connection, "send") as mock_mail_send:
        for method in [client.get, client.put, client.delete, client.patch]:
            response: werkzeug.test.WrapperTestResponse = method(
                tests.DDSEndpoint.MOTD_SEND, headers=token, json={"motd_id": "something"}
            )
            assert response.status_code == http.HTTPStatus.METHOD_NOT_ALLOWED
        assert mock_mail_send.call_count == 0


def test_send_motd_not_superadmin(client: flask.testing.FlaskClient) -> None:
    """Only Super Admins should be able to send the motds."""
    for role in ["Unit Admin", "Unit Personnel", "Researcher"]:
        # Authenticate
        token: typing.Dict = get_token(username=users[role], client=client)

        # Attempt request
        with unittest.mock.patch.object(flask_mail.Connection, "send") as mock_mail_send:
            response: werkzeug.test.WrapperTestResponse = client.post(
                tests.DDSEndpoint.MOTD_SEND, headers=token, json={"motd_id": "something"}
            )
            assert response.status_code == http.HTTPStatus.FORBIDDEN
            assert mock_mail_send.call_count == 0


def test_send_motd_no_json(client: flask.testing.FlaskClient) -> None:
    """The request needs json in order to send a motd."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Attempt request
    with unittest.mock.patch.object(flask_mail.Connection, "send") as mock_mail_send:
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.MOTD_SEND, headers=token
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Required data missing from request" in response.json.get("message")
        assert mock_mail_send.call_count == 0


def test_send_motd_no_motdid(client: flask.testing.FlaskClient) -> None:
    """The json should have motd_id."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Attempt request
    with unittest.mock.patch.object(flask_mail.Connection, "send") as mock_mail_send:
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.MOTD_SEND, headers=token, json={"test": "something"}
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Please specify the ID of the MOTD you want to send." in response.json.get("message")
        assert mock_mail_send.call_count == 0


def test_send_motd_nonexistent_motd(client: flask.testing.FlaskClient) -> None:
    """The motd_id needs to be a valid motd."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Specify motd to send
    motd_id: int = 10

    # Attempt request
    with unittest.mock.patch.object(flask_mail.Connection, "send") as mock_mail_send:
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.MOTD_SEND, headers=token, json={"motd_id": motd_id}
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert f"There is no active MOTD with ID '{motd_id}'" in response.json.get("message")
        assert mock_mail_send.call_count == 0


def test_send_motd_not_active(client: flask.testing.FlaskClient) -> None:
    """Attempt sending a motd which is not active."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Create a motd
    message: str = "This is a message that should become a MOTD and then be sent to all the users."
    new_motd: models.MOTD = models.MOTD(message=message, active=False)
    db.session.add(new_motd)
    db.session.commit()

    # Make sure the motd is created
    created_motd: models.MOTD = models.MOTD.query.filter_by(message=message).one_or_none()
    assert created_motd and not created_motd.active

    # Attempt request
    with unittest.mock.patch.object(flask_mail.Connection, "send") as mock_mail_send:
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.MOTD_SEND, headers=token, json={"motd_id": created_motd.id}
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert f"There is no active MOTD with ID '{created_motd.id}'" in response.json.get(
            "message"
        )
        assert mock_mail_send.call_count == 0


def test_send_motd_no_primary_email(client: flask.testing.FlaskClient, mock_queue_redis) -> None:
    """Send a motd to all users."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Create a motd
    message: str = "This is a message that should become a MOTD and then be sent to all the users."
    new_motd: models.MOTD = models.MOTD(message=message)
    db.session.add(new_motd)
    db.session.commit()

    # Make sure the motd is created
    created_motd: models.MOTD = models.MOTD.query.filter_by(message=message).one_or_none()
    assert created_motd

    # Get number of users
    num_users: int = models.User.query.count()

    # Remove primary_email for one user
    primary_email: models.Email = models.Email.query.first()
    email: str = primary_email.email
    username: str = primary_email.user.username
    db.session.delete(primary_email)
    db.session.commit()

    # Make sure email is removed
    assert not models.Email.query.filter_by(email=email).one_or_none()
    assert not models.User.query.filter_by(username=username).one().primary_email

    # Attempt request and catch email
    with mail.record_messages() as outbox:
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.MOTD_SEND, headers=token, json={"motd_id": created_motd.id}
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(outbox) == num_users - 1
        assert "Important Information: Data Delivery System" in outbox[-1].subject
        assert "incorrect subject" not in outbox[-1].subject


def test_send_motd_incorrect_type_unit_only(client: flask.testing.FlaskClient) -> None:
    """The parameter unit_only should be a boolean"""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Create a motd
    message: str = "This is a message that should become a MOTD and then be sent to all the users."
    new_motd: models.MOTD = models.MOTD(message=message)
    db.session.add(new_motd)
    db.session.commit()

    # Make sure the motd is created
    created_motd: models.MOTD = models.MOTD.query.filter_by(message=message).one_or_none()
    assert created_motd

    # Attempt request
    with unittest.mock.patch.object(flask_mail.Connection, "send") as mock_mail_send:
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.MOTD_SEND,
            headers=token,
            json={"motd_id": created_motd.id, "unit_only": "some_string"},
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "The 'unit_only' argument must be a boolean." in response.json.get("message")
        assert mock_mail_send.call_count == 0


def test_send_motd_ok_all(client: flask.testing.FlaskClient, mock_queue_redis) -> None:
    """Send a motd to all users."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Create a motd
    message: str = "This is a message that should become a MOTD and then be sent to all the users."
    new_motd: models.MOTD = models.MOTD(message=message)
    db.session.add(new_motd)
    db.session.commit()

    # Make sure the motd is created
    created_motd: models.MOTD = models.MOTD.query.filter_by(message=message).one_or_none()
    assert created_motd

    # Get number of users
    num_users = models.User.query.count()

    # Attempt request and catch email
    with mail.record_messages() as outbox:
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.MOTD_SEND,
            headers=token,
            json={"motd_id": created_motd.id, "unit_only": False},
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(outbox) == num_users
        assert "Important Information: Data Delivery System" in outbox[-1].subject


def test_send_motd_ok_unitusers(client: flask.testing.FlaskClient, mock_queue_redis) -> None:
    """Send a motd to all unitusers users."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Create a motd
    message: str = "This is a message that should become a MOTD and then be sent to all the users."
    new_motd: models.MOTD = models.MOTD(message=message)
    db.session.add(new_motd)
    db.session.commit()

    # Make sure the motd is created
    created_motd: models.MOTD = models.MOTD.query.filter_by(message=message).one_or_none()
    assert created_motd

    # Get number of users
    num_users = models.UnitUser.query.count()

    # Attempt request and catch email
    with mail.record_messages() as outbox:
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.MOTD_SEND,
            headers=token,
            json={"motd_id": created_motd.id, "unit_only": True},
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(outbox) == num_users
        assert "Important Information: Data Delivery System" in outbox[-1].subject


# Maintenance ######################################################################################


def test_set_maintenance_not_superadmin(client: flask.testing.FlaskClient) -> None:
    """Change Maintenance mode using everything but Super Admin access."""
    no_access_users: typing.Dict = users.copy()
    no_access_users.pop("Super Admin")

    for u in no_access_users:
        token: typing.Dict = get_token(username=users[u], client=client)
        response: werkzeug.test.WrapperTestResponse = client.put(
            tests.DDSEndpoint.MAINTENANCE, headers=token, json={"state": "on"}
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_get_maintenance_status_not_superadmin(client: flask.testing.FlaskClient) -> None:
    """Check Maintenance mode status using everything but Super Admin access."""
    no_access_users: typing.Dict = users.copy()
    no_access_users.pop("Super Admin")

    for u in no_access_users:
        token: typing.Dict = get_token(username=users[u], client=client)
        response: werkzeug.test.WrapperTestResponse = client.get(
            tests.DDSEndpoint.MAINTENANCE, headers=token
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_maintenance_command_incorrect_method(client: flask.testing.FlaskClient) -> None:
    """Only put and get should be accepted."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Attempt request
    for method in [client.post, client.delete, client.patch]:
        response: werkzeug.test.WrapperTestResponse = method(
            tests.DDSEndpoint.MAINTENANCE, headers=token, json={"state": "on"}
        )
        assert response.status_code == http.HTTPStatus.METHOD_NOT_ALLOWED


def test_set_maintenance_no_json(client: flask.testing.FlaskClient) -> None:
    """The request needs json in order to change Maintenance mode."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Attempt request
    response: werkzeug.test.TestResponse = client.put(tests.DDSEndpoint.MAINTENANCE, headers=token)
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing from request" in response.json.get("message")


def test_get_maintenance_status_no_json_required(client: flask.testing.FlaskClient) -> None:
    """No json needed in order to get the current Maintenance mode."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Attempt request
    response: werkzeug.test.TestResponse = client.get(tests.DDSEndpoint.MAINTENANCE, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    assert "Maintenance mode is set to:" in response.json.get("message")


def test_set_maintenance_incorrect_state(client: flask.testing.FlaskClient) -> None:
    """The json should be 'on' or 'off'."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # create record in Maintenance
    current_mode: models.Maintenance = models.Maintenance(active=False)
    db.session.add(current_mode)
    db.session.commit()
    # Attempt request
    response: werkzeug.test.WrapperTestResponse = client.put(
        tests.DDSEndpoint.MAINTENANCE, headers=token, json={"state": "something"}
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Please, specify the correct argument: on or off" in response.json.get("message")


def test_set_maintenance_on_ok(client: flask.testing.FlaskClient) -> None:
    """Set Maintenance mode to 'on'."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)
    setting = "on"

    # create record in Maintenance
    current_mode: models.Maintenance = models.Maintenance(active=False)
    db.session.add(current_mode)
    db.session.commit()

    # Verify that maintenance is off
    assert models.Maintenance.query.first().active is False

    # Attempt request
    response: werkzeug.test.WrapperTestResponse = client.put(
        tests.DDSEndpoint.MAINTENANCE, headers=token, json={"state": setting}
    )
    assert response.status_code == http.HTTPStatus.OK
    assert f"Maintenance set to: {setting.upper()}" in response.json.get("message")

    # Verify that maintenance is set to ON using the get method
    response: werkzeug.test.TestResponse = client.get(tests.DDSEndpoint.MAINTENANCE, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    assert f"Maintenance mode is set to: {setting.upper()}" in response.json.get("message")


def test_set_maintenance_off_ok(client: flask.testing.FlaskClient) -> None:
    """Set Maintenance mode to 'off'."""
    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)
    setting = "off"

    # create record in Maintenance
    current_mode: models.Maintenance = models.Maintenance.query.first()
    current_mode.active = True
    db.session.commit()

    # Verify that maintenance is on
    assert models.Maintenance.query.first().active

    # Attempt request
    response: werkzeug.test.WrapperTestResponse = client.put(
        tests.DDSEndpoint.MAINTENANCE, headers=token, json={"state": setting}
    )
    assert response.status_code == http.HTTPStatus.OK
    assert f"Maintenance set to: {setting.upper()}" in response.json.get("message")

    # Verify that maintenance is set to OFF using the get method
    response: werkzeug.test.TestResponse = client.get(tests.DDSEndpoint.MAINTENANCE, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    assert f"Maintenance mode is set to: {setting.upper()}" in response.json.get("message")


# AnyProjectsBusy

# -- get


def test_anyprojectsbusy_no_token(client: flask.testing.FlaskClient) -> None:
    """Token required to check if projects are busy."""
    response = client.get(tests.DDSEndpoint.PROJECT_BUSY_ANY, headers=tests.DEFAULT_HEADER)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    assert response.json.get("message")
    assert "No token" in response.json.get("message")


def test_anyprojectsbusy_not_allowed(client: flask.testing.FlaskClient) -> None:
    """Only super admins allowed."""
    for role in ["researcher", "unituser", "unitadmin"]:
        token = tests.UserAuth(tests.USER_CREDENTIALS[role]).token(client)
        response = client.get(
            tests.DDSEndpoint.PROJECT_BUSY_ANY,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_anyprojectsbusy_true(client: flask.testing.FlaskClient) -> None:
    """There are busy projects."""
    # Get a project and set to busy
    project: models.Project = models.Project.query.first()
    project.busy = True
    db.session.commit()
    busy_count: int = models.Project.query.filter_by(busy=True).count()
    assert busy_count > 0

    # Call endpoint
    token = tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client)
    response = client.get(
        tests.DDSEndpoint.PROJECT_BUSY_ANY,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.OK

    # Check response
    num: int = response.json.get("num")
    assert num == busy_count


def test_anyprojectsbusy_false(client: flask.testing.FlaskClient) -> None:
    """There are busy projects."""
    # Set all projects to not busy
    for project in models.Project.query.all():
        project.busy = False
    db.session.commit()
    busy_count: int = models.Project.query.filter_by(busy=True).count()
    assert busy_count == 0

    # Call endpoint
    token = tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client)
    response = client.get(
        tests.DDSEndpoint.PROJECT_BUSY_ANY,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.OK

    # Check response
    num: int = response.json.get("num")
    assert num == 0


def test_anyprojectsbusy_true_list(client: flask.testing.FlaskClient) -> None:
    """There are busy projects, list them."""
    wanted_return_info: typing.Dict = {}

    # Get all projects and set to busy
    all_projects: typing.List = models.Project.query.all()
    for project in all_projects:
        project.busy = True
        wanted_return_info[project.public_id] = project.date_updated
    db.session.commit()
    busy_count: int = models.Project.query.filter_by(busy=True).count()
    assert busy_count == len(all_projects)

    # Call endpoint
    token = tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client)
    response = client.get(
        tests.DDSEndpoint.PROJECT_BUSY_ANY, headers=token, query_string={"list": True}
    )
    assert response.status_code == http.HTTPStatus.OK

    # Check response
    num: int = response.json.get("num")
    assert num == len(all_projects)
    projects_returned: typing.Dict = response.json.get("projects")
    for p in wanted_return_info:
        assert p in projects_returned


def test_anyprojectsbusy_false_list(client: flask.testing.FlaskClient) -> None:
    """There are busy projects."""
    # Get all projects and set to not busy
    all_projects: typing.List = models.Project.query.all()
    for project in all_projects:
        project.busy = False
    db.session.commit()
    busy_count: int = models.Project.query.filter_by(busy=True).count()
    assert busy_count == 0

    # Call endpoint
    token = tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client)
    response = client.get(
        tests.DDSEndpoint.PROJECT_BUSY_ANY, headers=token, query_string={"list": True}
    )
    assert response.status_code == http.HTTPStatus.OK

    # Check response
    num: int = response.json.get("num")
    assert num == 0
    projects_returned: typing.Dict = response.json.get("projects")
    assert projects_returned is None


def test_statistics_no_access(client: flask.testing.FlaskClient) -> None:
    """Verify that users that are not Super Admins cannot use this endpoint."""
    # Verify no access for researchers and unit users
    for user in ["researcher", "unituser", "unitadmin"]:
        token = tests.UserAuth(tests.USER_CREDENTIALS[user]).token(client)
        response = client.get(tests.DDSEndpoint.STATS, headers=token)
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_statistics_return_none(client: flask.testing.FlaskClient) -> None:
    """There are no rows in the Reporting table."""
    # Check that there are no rows
    assert not models.Reporting.query.count()

    # Get all rows from API
    token = tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client)
    response = client.get(tests.DDSEndpoint.STATS, headers=token)
    assert response.status_code == http.HTTPStatus.OK

    # Check response
    returned: typing.Dict = response.json.get("stats")
    assert returned == []


def test_statistics_return_rows(client: flask.testing.FlaskClient, cli_runner) -> None:
    """Verify list returned when there are rows in reporting table."""

    def add_row_to_reporting_table(time):
        """Run command to add a new row to the reporting table."""
        with freezegun.freeze_time(time):
            # Run scheduled job now
            with mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
                result: click.testing.Result = cli_runner.invoke(collect_stats)
                assert not result.exception, "Raised an unwanted exception."
                assert mock_mail_send.call_count == 0

    # Generate row in reporting table
    time_1 = datetime(year=2022, month=12, day=10, hour=10, minute=54, second=10)
    add_row_to_reporting_table(time=time_1)

    # Verify that there's a row added
    assert models.Reporting.query.count() == 1

    # Get all rows from API
    token = tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client)
    response = client.get(tests.DDSEndpoint.STATS, headers=token)
    assert response.status_code == http.HTTPStatus.OK

    # Check response
    returned: typing.Dict = response.json.get("stats")
    assert len(returned) == 1
    reporting_row = models.Reporting.query.first()
    assert returned[0] == {
        "Date": str(reporting_row.date.date()),
        "Units": reporting_row.unit_count,
        "Researchers": reporting_row.researcher_count,
        "Project Owners": reporting_row.project_owner_unique_count,
        "Unit Personnel": reporting_row.unit_personnel_count,
        "Unit Admins": reporting_row.unit_admin_count,
        "Super Admins": reporting_row.superadmin_count,
        "Total Users": reporting_row.total_user_count,
        "Total Projects": reporting_row.total_project_count,
        "Active Projects": reporting_row.active_project_count,
        "Inactive Projects": reporting_row.inactive_project_count,
        "Data Now (TB)": reporting_row.tb_stored_now,
        "Data Uploaded (TB)": reporting_row.tb_uploaded_since_start,
        "TBHours Last Month": reporting_row.tbhours,
        "TBHours Total": reporting_row.tbhours_since_start,
    }
    returned_columns: typing.Dict = response.json.get("columns")
    assert returned_columns


# UnitUserEmails


def test_unituseremails_accessdenied(client: flask.testing.FlaskClient) -> None:
    """Only Super Admins can get the emails."""
    no_access_users: typing.Dict = users.copy()
    no_access_users.pop("Super Admin")

    for u in no_access_users:
        token: typing.Dict = get_token(username=users[u], client=client)
        response: werkzeug.test.WrapperTestResponse = client.get(
            tests.DDSEndpoint.USER_EMAILS, headers=token
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_unituseremails_no_emails(client: flask.testing.FlaskClient) -> None:
    """Empty should be returned if no emails."""
    # No users returned from query
    with patch("dds_web.database.models.UnitUser.query") as mock_users:
        mock_users.return_value = []

        # Authenticate
        token: typing.Dict = get_token(username=users["Super Admin"], client=client)

        # Call endpoint
        response: werkzeug.test.WrapperTestResponse = client.get(
            tests.DDSEndpoint.USER_EMAILS, headers=token
        )
        assert response.status_code == http.HTTPStatus.OK

        # Verify response
        assert response.json and response.json.get("empty") == True


def test_unituseremails_ok(client: flask.testing.FlaskClient) -> None:
    """Return user emails for unit users only."""
    # Emails that should be returned
    unituser_emails = [user.primary_email for user in models.UnitUser.query.all()]

    # Emails that should not be returned
    researcher_emails = [user.primary_email for user in models.ResearchUser.query.all()]
    superadmin_emails = [user.primary_email for user in models.SuperAdmin.query.all()]
    non_primary_emails = [
        email.email for email in models.Email.query.filter_by(primary=False).all()
    ]

    # Authenticate
    token: typing.Dict = get_token(username=users["Super Admin"], client=client)

    # Call endpoint
    response: werkzeug.test.WrapperTestResponse = client.get(
        tests.DDSEndpoint.USER_EMAILS, headers=token
    )
    assert response.status_code == http.HTTPStatus.OK

    # Verify response -------------------------------

    # There should be a json response
    json_response = response.json
    assert json_response

    # There should be emails in response
    emails = json_response.get("emails")
    assert emails

    # The list of emails should contain all unit user primary emails
    assert len(emails) == len(unituser_emails)
    for e in unituser_emails:
        assert e in emails

    # The list of should not contain any of the other emails
    for e in researcher_emails + superadmin_emails + non_primary_emails:
        assert e not in emails
