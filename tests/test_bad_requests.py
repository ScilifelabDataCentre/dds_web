"""
Make empty/bad requests to all endpoints.

No assertions, only checking whether any uncaught exceptions are thrown.
"""

from dds_web import db
import tests

ENDPOINTS = dict(tests.DDSEndpoint.__dict__)
del ENDPOINTS["TIMEOUT"]
del ENDPOINTS["__dict__"]
del ENDPOINTS["__weakref__"]
del ENDPOINTS["__module__"]
del ENDPOINTS["__doc__"]


def run_requests(run_func):
    for req_type in ("DELETE", "GET", "PATCH", "POST", "PUT"):
        for endpoint in ENDPOINTS:
            run_func(req_type, ENDPOINTS[endpoint])


def test_empty_requests(client):
    """Make empty requests to all endpoints."""

    def make_req(req_type, endp):
        return client.open(
            endp,
            method=req_type,
        )

    run_requests(make_req)


def test_empty_json(client):
    """Make requests with empty json to all endpoints."""

    def make_req(req_type, endp):
        return client.open(
            endp,
            json={},
            method=req_type,
        )

    run_requests(make_req)


def test_incorrect_json(client):
    """Make requests with incorrect (not what is expected) json to all endpoints."""

    def make_req(req_type, endp):
        return client.open(
            endp,
            json={"incorrect": True},
            method=req_type,
        )

    run_requests(make_req)


def test_invalid_json(client):
    """Make requests with invalid json to all endpoints."""

    def make_req(req_type, endp):
        return client.open(
            endp,
            data="invalid",
            content_type="application/json",
            method=req_type,
        )

    run_requests(make_req)


def test_auth_empty_requests(client):
    """Make authenticated empty requests to all endpoints."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)

    def make_req(req_type, endp):
        return client.open(
            endp,
            headers=token,
            method=req_type,
        )

    run_requests(make_req)


def test_get_auth_empty_json(client):
    """Make authenticated requests with empty json to all endpoints."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)

    def make_req(req_type, endp):
        return client.open(
            endp,
            headers=token,
            json={},
            method=req_type,
        )

    run_requests(make_req)


def test_get_auth_incorrect_json(client):
    """Make authenticated requests with incorrect (not what is expected) json to all endpoints."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)

    def make_req(req_type, endp):
        return client.open(
            endp,
            headers=token,
            json={"incorrect": True},
            method=req_type,
        )

    run_requests(make_req)


def test_get_auth_invalid_json(client):
    """Make authenticated requests with invalid json to all endpoints."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)

    def make_req(req_type, endp):
        return client.open(
            endp,
            headers=token,
            data="invalid",
            content_type="application/json",
            method=req_type,
        )

    run_requests(make_req)
