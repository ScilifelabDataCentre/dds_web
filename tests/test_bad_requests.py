"""
Make empty/bad requests to all endpoints.

No assertions, only checking whether any uncaught exceptions are thrown.
"""

from dds_web import db
import tests

ENDPOINTS = dict(tests.DDSEndpoint.__dict__)
del ENDPOINTS["TIMEOUT"]
del ENDPOINTS["PASSWORD_RESET_COMPLETED"]
del ENDPOINTS["__dict__"]
del ENDPOINTS["__weakref__"]
del ENDPOINTS["__module__"]
del ENDPOINTS["__doc__"]


def run_requests(client, args: dict):
    """Helper function to run requests with endpoints and methods."""
    for req_type in ("DELETE", "GET", "PATCH", "POST", "PUT"):
        for endpoint in ENDPOINTS:
            client.open(ENDPOINTS[endpoint], method=req_type, **args)


def test_empty_requests(client):
    """Make empty requests to all endpoints."""
    args = {}
    run_requests(client, args)


def test_empty_json(client):
    """Make requests with empty json to all endpoints."""
    args = {"json": {}}

    run_requests(client, args)


def test_incorrect_json(client):
    """Make requests with incorrect (not what is expected) json to all endpoints."""
    args = {"json": {"incorrect": True}}

    run_requests(client, args)


def test_invalid_json(client):
    """Make requests with invalid json to all endpoints."""
    args = {"data": "invalid", "content_type": "application/json"}

    run_requests(client, args)


def test_auth_empty_requests(client):
    """Make authenticated empty requests to all endpoints."""
    args = {"headers": tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)}

    run_requests(client, args)


def test_get_auth_empty_json(client):
    """Make authenticated requests with empty json to all endpoints."""
    args = {
        "headers": tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        "json": {},
    }

    run_requests(client, args)


def test_get_auth_incorrect_json(client):
    """Make authenticated requests with incorrect (not what is expected) json to all endpoints."""
    args = {
        "headers": tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        "json": {"incorrect": True},
    }

    run_requests(client, args)


def test_get_auth_invalid_json(client):
    """Make authenticated requests with invalid json to all endpoints."""
    args = {
        "headers": tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        "data": "invalid",
        "content_type": "application/json",
    }

    run_requests(client, args)
