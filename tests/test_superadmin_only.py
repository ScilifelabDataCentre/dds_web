# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import time

# Own
from dds_web.database import models
import tests

# CONFIG ################################################################################## CONFIG #

users = {
    "Researcher": "researchuser",
    "Unit Personnel": "unituser",
    "Unit Admin": "unitadmin",
    "Super Admin": "superadmin",
}

# TESTS #################################################################################### TESTS #


def get_token(username, client):
    return tests.UserAuth(tests.USER_CREDENTIALS[username]).token(client)


# AllUnits


def test_list_units_as_not_superadmin(client):
    """Only Super Admin can list users."""
    no_access_users = users.copy()
    no_access_users.pop("Super Admin")

    for u in no_access_users:
        token = get_token(username=users[u], client=client)
        response = client.get(tests.DDSEndpoint.LIST_UNITS_ALL, headers=token)
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_list_units_as_super_admin(client):
    """List units as Super Admin."""
    all_units = models.Unit.query.all()

    token = get_token(username=users["Super Admin"], client=client)
    response = client.get(tests.DDSEndpoint.LIST_UNITS_ALL, headers=token)
    assert response.status_code == http.HTTPStatus.OK

    keys = response.json.get("keys")
    units = response.json.get("units")
    assert keys and units

    assert keys == [
        "Name",
        "Public ID",
        "External Display Name",
        "Days In Available",
        "Days In Expired",
        "Safespring Endpoint",
        "Contact Email",
    ]
    assert len(all_units) == len(units)

    for unit in all_units:
        expected = {
            "Name": unit.name,
            "Public ID": unit.public_id,
            "External Display Name": unit.external_display_name,
            "Contact Email": unit.contact_email,
            "Safespring Endpoint": unit.safespring_endpoint,
            "Days In Available": unit.days_in_available,
            "Days In Expired": unit.days_in_expired,
        }
        assert expected in units


# MOTD


def test_create_motd_not_superadmin(client):
    """Create a new message of the day, using everything but Super Admin access."""
    no_access_users = users.copy()
    no_access_users.pop("Super Admin")

    for u in no_access_users:
        token = get_token(username=users[u], client=client)
        response = client.post(tests.DDSEndpoint.MOTD, headers=token)
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_create_motd_as_superadmin_no_json(client):
    """Create a new message of the day, using a Super Admin account, but without any json."""
    token = get_token(username=users["Super Admin"], client=client)
    response = client.post(tests.DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing from request!" in response.json.get("message")


def test_create_motd_as_superadmin_no_message(client):
    """Create a new message of the day, using a Super Admin account, but without any message."""
    token = get_token(username=users["Super Admin"], client=client)
    response = client.post(tests.DDSEndpoint.MOTD, headers=token, json={"test": "test"})
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "No MOTD specified." in response.json.get("message")


def test_create_motd_as_superadmin_empty_message(client):
    """Create a new message of the day, using a Super Admin account, but with empty message."""
    token = get_token(username=users["Super Admin"], client=client)
    response = client.post(tests.DDSEndpoint.MOTD, headers=token, json={"message": ""})
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "No MOTD specified." in response.json.get("message")


def test_create_motd_as_superadmin_success(client):
    """Create a new message of the day, using a Super Admin account."""
    token = get_token(username=users["Super Admin"], client=client)
    response = client.post(tests.DDSEndpoint.MOTD, headers=token, json={"message": "test"})
    assert response.status_code == http.HTTPStatus.OK
    assert "The MOTD was successfully added to the database." in response.json.get("message")

    assert models.MOTD.query.filter_by(message="test")


def test_get_motd_no_message(client):
    """Get latest MOTD from database."""
    response = client.get(tests.DDSEndpoint.MOTD, headers={"X-CLI-Version": "0.0.0"})
    assert response.status_code == http.HTTPStatus.OK
    assert not response.json.get("message")


def test_get_motd(client):
    """Get latest MOTD from database."""
    # Create first message
    token = get_token(username=users["Super Admin"], client=client)
    response = client.post(tests.DDSEndpoint.MOTD, headers=token, json={"message": "test"})
    assert response.status_code == http.HTTPStatus.OK
    assert models.MOTD.query.filter_by(message="test")

    # Get first message
    response1 = client.get(tests.DDSEndpoint.MOTD, headers={"X-CLI-Version": "0.0.0"})
    assert response1.status_code == http.HTTPStatus.OK
    assert "test" in response1.json.get("message")

    time.sleep(5)

    # Create new message
    response2 = client.post(
        tests.DDSEndpoint.MOTD, headers=token, json={"message": "something else"}
    )
    assert response2.status_code == http.HTTPStatus.OK
    assert models.MOTD.query.filter_by(message="something else")

    # Check that new message is displayed
    response3 = client.get(tests.DDSEndpoint.MOTD, headers={"X-CLI-Version": "0.0.0"})
    assert response3.status_code == http.HTTPStatus.OK
    assert "something else" in response3.json.get("message")


# AllUsers


def test_get_all_users_wrong_user(client):
    """Try to get all users when not Super Admin."""
    no_access_users = users.copy()
    no_access_users.pop("Super Admin")

    for u in no_access_users:
        token = get_token(username=users[u], client=client)
        response = client.get(tests.DDSEndpoint.LIST_USERS, headers=token)
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_get_all_users_correct(client):
    """Get list of all users when Super Admin."""
    # Get list of users
    token = get_token(username=users["Super Admin"], client=client)
    response = client.get(tests.DDSEndpoint.LIST_USERS, headers=token)
    assert response.status_code == http.HTTPStatus.OK

    # Get expected results
    response_json = response.json
    users = response_json.get("users")
    keys = response_json.get("keys")
    empty = response_json.get("empty")

    # Verify all returned
    assert users and keys
    assert empty is False  # not empty also gives True for None
    assert keys == ["Name", "Username", "Email", "Role", "Active"]

    # Verify all users returned
    users_correct = [
        {
            "Name": user.name,
            "Username": user.username,
            "Email": user.primary_email,
            "Role": user.role,
            "Active": user.is_active,
        }
        for user in models.User.query.all()
    ]
    for x in users_correct:
        assert x in users


def test_check_specific_user_no_specified(client):
    """Check if a none user is in the database."""
    token = get_token(username=users["Super Admin"], client=client)
    response = client.get(tests.DDSEndpoint.LIST_USERS, headers=token, json={"username": ""})
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Username required to check existence of account." in response.json.get("message")


def test_check_specific_user_non_existent(client):
    """Check if a non existent user is in the database."""
    token = get_token(username=users["Super Admin"], client=client)

    # Non existing user
    username = "nonexistinguser"
    response = client.get(tests.DDSEndpoint.LIST_USERS, headers=token, json={"username": username})
    assert response.status_code == http.HTTPStatus.OK

    response_json = response.json
    assert response_json

    exists = response_json.get("exists")
    assert exists is False


def test_check_specific_user_ok(client):
    """Check if a non existent user is in the database."""
    token = get_token(username=users["Super Admin"], client=client)

    # Existing user
    user = models.User.query.first()
    assert user

    response = client.get(
        tests.DDSEndpoint.LIST_USERS, headers=token, json={"username": user.username}
    )
    assert response.status_code == http.HTTPStatus.OK

    response_json = response.json
    assert response_json

    exists = response_json.get("exists")
    assert exists is True
