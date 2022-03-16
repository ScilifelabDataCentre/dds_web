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
