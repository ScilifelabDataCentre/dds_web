from base64 import b64encode
import json

proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}


def test_create_project_without_credentials(client):
    credentials = b64encode(b"username:password").decode("utf-8")
    response = client.post(
        "/api/v1/proj/create",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status == "403 FORBIDDEN"


def test_create_project_with_credentials(client):
    credentials = b64encode(b"admin:password").decode("utf-8")
    response = client.post(
        "/api/v1/proj/create",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status == "200 OK"


def test_create_project_without_title_description(client):
    credentials = b64encode(b"admin:password").decode("utf-8")
    response = client.post(
        "/api/v1/proj/create",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps({"pi": "piName"}),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"


def test_create_project_with_malformed_json(client):
    credentials = b64encode(b"admin:password").decode("utf-8")
    response = client.post(
        "/api/v1/proj/create",
        headers={"Authorization": f"Basic {credentials}"},
        data="",
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"


def test_create_project_by_user_with_no_unit(client):
    credentials = b64encode(b"admin2:password").decode("utf-8")
    response = client.post(
        "/api/v1/proj/create",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status == "403 FORBIDDEN"
