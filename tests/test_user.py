from base64 import b64encode
import json
from dds_web import db
from dds_web.database import models


def test_add_user_without_credentials(client):

    new_user_data = {"email": "first_email@mailtrap.io"}
    credentials = b64encode(b"").decode("utf-8")

    response = client.post(
        "/api/v1/user/add",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps(new_user_data),
        content_type="application/json",
    )
    assert response.status == "401 UNAUTHORIZED"

    invited_user = (
        db.session.query(models.Invite).filter_by(email=new_user_data["email"]).one_or_none()
    )
    assert invited_user is None


def test_add_user_with_unitadmin_without_user_data(client):
    credentials = b64encode(b"unitadmin:password").decode("utf-8")
    response = client.post(
        "/api/v1/user/add",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps({}),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"


def test_add_user_with_unitadmin_without_role(client):
    credentials = b64encode(b"unitadmin:password").decode("utf-8")
    response = client.post(
        "/api/v1/user/add",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps({"email": "first_test_email@mailtrap.io"}),
        content_type="application/json",
    )
    assert response.status == "500 SERVER ERROR"


def test_add_user_with_unitadmin_with_extraargs(client):
    credentials = b64encode(b"unitadmin:password").decode("utf-8")
    response = client.post(
        "/api/v1/user/add",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps({"email": "first_test_email@mailtrap.io", "extra": "extrainfo"}),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"


def test_add_user_with_unitadmin_and_invalid_role(client):
    invite_info = {"email": "first_test_email@mailtrap.io", "role": "Invalid Role"}
    credentials = b64encode(b"unitadmin:password").decode("utf-8")

    response = client.post(
        "/api/v1/user/add",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps(invite_info),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"

    invited_user = (
        db.session.query(models.Invite).filter_by(email=invite_info["email"]).one_or_none()
    )
    assert invited_user is None


def test_add_user_with_unitadmin_and_invalid_email(client):
    invite_info = {"email": "first_test_email", "role": "Researcher"}
    credentials = b64encode(b"unitadmin:password").decode("utf-8")

    response = client.post(
        "/api/v1/user/add",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps(invite_info),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"

    invited_user = (
        db.session.query(models.Invite).filter_by(email=invite_info["email"]).one_or_none()
    )
    assert invited_user is None


def test_add_user_with_unitadmin(client):

    invite_info = {"email": "first_test_email@mailtrap.io", "role": "Researcher"}
    credentials = b64encode(b"unitadmin:password").decode("utf-8")
    response = client.post(
        "/api/v1/user/add",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps(invite_info),
        content_type="application/json",
    )
    assert response.status == "200 OK"

    invited_user = (
        db.session.query(models.Invite).filter_by(email=invite_info["email"]).one_or_none()
    )
    assert invited_user
    assert invited_user.email == invite_info["email"]
    assert invited_user.role == invite_info["Researcher"]


def test_add_user_existing_email(client):
    invite_info = {"email": "first_test_email@mailtrap.io", "role": "Researcher"}
    credentials = b64encode(b"unitadmin:password").decode("utf-8")
    response = client.post(
        "/api/v1/user/add",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps(invite_info),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"


def test_add_user_with_unitpersonnel_permission_denied(client):
    invite_info = {"email": "second_test_email@mailtrap.io", "role": "Unit Admin"}
    credentials = b64encode(b"unituser:password").decode("utf-8")
    response = client.post(
        "/api/v1/user/add",
        headers={"Authorization": f"Basic {credentials}"},
        data=json.dumps(invite_info),
        content_type="application/json",
    )
    assert response.status == "400 PERMISSION DENIED"

    invited_user = (
        db.session.query(models.Invite).filter_by(email=invite_info["email"]).one_or_none()
    )
    assert invited_user is None
