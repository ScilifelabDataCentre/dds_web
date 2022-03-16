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


def test_list_unitusers_with_researcher(client):
    """Researchers cannot list unit users."""
    token = get_token(username=users["Researcher"], client=client)
    response = client.get(tests.DDSEndpoint.LIST_UNIT_USERS, headers=token)
    assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_list_unitusers_with_unit_personnel_and_admin_deactivated(client):
    """Unit Personnel should be able to list the users within a unit."""
    # Deactivate user
    for u in ["Unit Personnel", "Unit Admin"]:
        # Get token
        token = get_token(username=users[u], client=client)

        user = models.User.query.get(users[u])
        user.active = False
        db.session.commit()

        # Try to list users - should only work if active - not now
        response = client.get(tests.DDSEndpoint.LIST_UNIT_USERS, headers=token)
        assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_list_unitusers_with_unit_personnel_and_admin_ok(client):
    # Active unit users should be able to list unit users
    for u in ["Unit Personnel", "Unit Admin"]:
        # Get token
        token = get_token(username=users[u], client=client)

        # Get users
        response = client.get(tests.DDSEndpoint.LIST_UNIT_USERS, headers=token)
        assert response.status_code == http.HTTPStatus.OK

        keys_in_response = response.json["keys"]
        unit_in_response = response.json["unit"]
        users_in_response = response.json["users"]

        assert keys_in_response

        user_object = models.User.query.get(users[u])
        assert user_object.unit.name == unit_in_response

        all_users = user_object.unit.users

        # ["Name", "Username", "Email", "Role", "Active"]
        for dbrow in user_object.unit.users:
            expected = {
                "Name": dbrow.name,
                "Username": dbrow.username,
                "Email": dbrow.primary_email,
                "Role": dbrow.role,
                "Active": dbrow.is_active,
            }
            assert expected in users_in_response


def test_list_unitusers_with_super_admin_no_unit(client):
    """Super admins need to specify a unit."""
    token = get_token(username=users["Super Admin"], client=client)
    response = client.get(tests.DDSEndpoint.LIST_UNIT_USERS, headers=token)
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Unit public id missing" in response.json.get("message")


def test_list_unitusers_with_super_admin_unit_empty(client):
    """Super admins need to specify a unit."""
    token = get_token(username=users["Super Admin"], client=client)
    for x in [None, ""]:
        response = client.get(tests.DDSEndpoint.LIST_UNIT_USERS, json={"unit": x}, headers=token)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Unit public id missing" in response.json.get("message")


def test_list_unitusers_with_super_admin_nonexistent_unit(client):
    """Super admins need to specify a correct unit."""
    incorrect_unit = "incorrect_unit"
    token = get_token(username=users["Super Admin"], client=client)
    response = client.get(
        tests.DDSEndpoint.LIST_UNIT_USERS, json={"unit": incorrect_unit}, headers=token
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert f"There is no unit with the public id '{incorrect_unit}'" in response.json.get("message")


def test_list_unitusers_with_super_admin_correct_unit(client):
    """Super admins can list users in a specific unit."""
    unit_row = models.Unit.query.filter_by(name="Unit 1").one_or_none()
    assert unit_row

    token = get_token(username=users["Super Admin"], client=client)
    response = client.get(
        tests.DDSEndpoint.LIST_UNIT_USERS, json={"unit": unit_row.public_id}, headers=token
    )
    assert response.status_code == http.HTTPStatus.OK

    assert all(x in response.json for x in ["users", "keys", "unit"])

    returned_users = response.json.get("users")
    returned_keys = response.json.get("keys")
    returned_unit = response.json.get("unit")

    assert returned_users and returned_keys and returned_unit
    assert returned_keys == ["Name", "Username", "Email", "Role", "Active"]
    assert returned_unit == unit_row.name
    assert len(returned_users) == len(unit_row.users)

    unit_users = [x["Username"] for x in returned_users]
    for x in unit_row.users:
        assert x.username in unit_users
