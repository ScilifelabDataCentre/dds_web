# Installed
import http
import unittest

# Own
import tests
from tests.test_user_delete import user_from_email


def test_get_info_unit_user(client):
    """Get info for unit user/Unit Admin"""

    response = client.get(
        tests.DDSEndpoint.USER_INFO,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    user_info = response.json["info"]

    assert user_info["email_primary"] == "unituser1@mailtrap.io"
    assert user_info["role"] == "Unit Personnel"
    assert user_info["username"] == "unituser"
    assert user_info["name"] == "Unit User"

    case = unittest.TestCase()
    case.assertCountEqual(user_info["emails_all"], ["unituser1@mailtrap.io"])

    response = client.get(
        tests.DDSEndpoint.USER_INFO,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    user_info = response.json["info"]

    assert user_info["email_primary"] == "unitadmin@mailtrap.io"
    assert user_info["role"] == "Unit Admin"
    assert user_info["username"] == "unitadmin"
    assert user_info["name"] == "Unit Admin"
    case.assertCountEqual(user_info["emails_all"], ["unitadmin@mailtrap.io"])
    assert user_info["is_admin"]


def test_get_info_research_user(client):
    """Get info for a research user"""

    response = client.get(
        tests.DDSEndpoint.USER_INFO,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    user_info = response.json["info"]

    assert user_info["email_primary"] == "researchuser@mailtrap.io"
    assert user_info["role"] == "Researcher"
    assert user_info["username"] == "researchuser"
    assert user_info["name"] == "Research User"
    case = unittest.TestCase()
    case.assertCountEqual(user_info["emails_all"], ["researchuser@mailtrap.io"])


def test_get_info_superadmin_user(client):
    """Get info for a super admin user"""

    response = client.get(
        tests.DDSEndpoint.USER_INFO,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
        content_type="application/json",
    )

    assert response.status_code == http.HTTPStatus.OK
    user_info = response.json["info"]

    assert user_info["email_primary"] == "superadmin@mailtrap.io"
    assert user_info["role"] == "Super Admin"
    assert user_info["username"] == "superadmin"
    assert user_info["name"] == "Super Admin"
    case = unittest.TestCase()
    case.assertCountEqual(user_info["emails_all"], ["superadmin@mailtrap.io"])


def test_show_usage_unit_user(client):
    """Show the amount of GB hours and the total cost for a unit"""
    # Preliminary test - to be expanded later
    response = client.get(
        tests.DDSEndpoint.USAGE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert "project_usage" in response.json.keys()
    assert "total_usage" in response.json.keys()
    unit_user = user_from_email("unituser1@mailtrap.io")
    case = unittest.TestCase()
    case.assertCountEqual(
        [x.public_id for x in unit_user.projects], response.json["project_usage"].keys()
    )
