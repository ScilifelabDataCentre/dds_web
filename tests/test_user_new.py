import json
import tests
import pytest


def test_no_form(client):
    response = client.post(tests.DDSEndpoint.USER_NEW, content_type="application/json")
    assert response.status == "400 BAD REQUEST"
