# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http

# Own
from dds_web import db
from dds_web.api import user
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
    """Create a new message of the day, using a Super Admin account, but without any json."""
    token = get_token(username=users["Super Admin"], client=client)
    response = client.post(tests.DDSEndpoint.MOTD, headers=token, json={"test": "test"})
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "No MOTD specified." in response.json.get("message")


def test_create_motd_as_superadmin_empty_message(client):
    """Create a new message of the day, using a Super Admin account, but without any json."""
    token = get_token(username=users["Super Admin"], client=client)
    response = client.post(tests.DDSEndpoint.MOTD, headers=token, json={"message": ""})
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "No MOTD specified." in response.json.get("message")


def test_create_motd_as_superadmin_success(client):
    """Create a new message of the day, using a Super Admin account, but without any json."""
    token = get_token(username=users["Super Admin"], client=client)
    response = client.post(tests.DDSEndpoint.MOTD, headers=token, json={"message": "test"})
    assert response.status_code == http.HTTPStatus.OK
    assert "The MOTD was successfully added to the database." in response.json.get("message")
