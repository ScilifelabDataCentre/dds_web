from base64 import b64encode
import json
from dds_web import db
from dds_web.database import models
import tests

first_new_email = {"email": "first_test_email@mailtrap.io"}
first_new_user = {**first_new_email, "role": "Researcher"}
first_new_user_extra_args = {**first_new_user, "extra": "test"}


def test_add_user_with_researcher(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).post_headers(),
        data=json.dumps(first_new_email),
        content_type="application/json",
    )
    assert response.status == "403 FORBIDDEN"
    invited_user = (
        db.session.query(models.Invite).filter_by(email=first_new_user["email"]).one_or_none()
    )
    assert invited_user is None


# def test_add_user_with_unituser_no_role(client):
#     response = client.post(
#         tests.DDSEndpoint.USER_ADD,
#         headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
#         data=json.dumps(first_new_email),
#         content_type="application/json",
#     )
#     assert response.status == "401 BAD REQUEST"
#     invited_user = (
#         db.session.query(models.Invite).filter_by(email=first_new_email["email"]).one_or_none()
#     )
#     assert invited_user is None


# def test_add_user_with_unitadmin_with_extraargs(client):
#     response = client.post(
#         tests.DDSEndpoint.USER_ADD,
#         headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
#         data=json.dumps(first_new_user_extra_args),
#         content_type="application/json",
#     )
#     assert response.status == "401 BAD REQUEST"
#     invited_user = (
#         db.session.query(models.Invite)
#         .filter_by(email=first_new_user_extra_args["email"])
#         .one_or_none()
#     )
#     assert invited_user is None


# def test_add_user_with_unitadmin_and_invalid_role(client):
#     new_user_data = {"email": "first_test_email@mailtrap.io", "role": "Invalid Role"}
#     credentials = b64encode(b"unitadmin:password").decode("utf-8")

#     response = client.post(
#         "/api/v1/user/add",
#         headers={"Authorization": f"Basic {credentials}"},
#         data=new_user_data,
#         content_type="application/json",
#     )
#     assert response.status == "400 BAD REQUEST"

#     invited_user = (
#         db.session.query(models.Invite).filter_by(email=new_user_data["email"]).one_or_none()
#     )
#     assert invited_user is None


# def test_add_user_with_unitadmin_and_invalid_email(client):
#     new_user_data = {"email": "first_test_email", "role": "Researcher"}
#     credentials = b64encode(b"unitadmin:password").decode("utf-8")

#     response = client.post(
#         "/api/v1/user/add",
#         headers={"Authorization": f"Basic {credentials}"},
#         data=new_user_data,
#         content_type="application/json",
#     )
#     assert response.status == "400 BAD REQUEST"

#     invited_user = (
#         db.session.query(models.Invite).filter_by(email=new_user_data["email"]).one_or_none()
#     )
#     assert invited_user is None


# def test_add_user_with_unitadmin(client):

#     new_user_data = {"email": "first_test_email@mailtrap.io", "role": "Researcher"}
#     credentials = b64encode(b"unitadmin:password").decode("utf-8")
#     response = client.post(
#         "/api/v1/user/add",
#         headers={"Authorization": f"Basic {credentials}"},
#         data=new_user_data,
#         content_type="application/json",
#     )
#     assert response.status == "200 OK"

#     invited_user = (
#         db.session.query(models.Invite).filter_by(email=new_user_data["email"]).one_or_none()
#     )
#     assert invited_user
#     assert invited_user.email == invite_info["email"]
#     assert invited_user.role == invite_info["Researcher"]


# def test_add_user_existing_email(client):
#     new_user_data = {"email": "first_test_email@mailtrap.io", "role": "Researcher"}
#     credentials = b64encode(b"unitadmin:password").decode("utf-8")
#     response = client.post(
#         "/api/v1/user/add",
#         headers={"Authorization": f"Basic {credentials}"},
#         data=new_user_data,
#         content_type="application/json",
#     )
#     assert response.status == "400 BAD REQUEST"


# def test_add_user_with_unitpersonnel_permission_denied(client):
#     new_user_data = {"email": "second_test_email@mailtrap.io", "role": "Unit Admin"}
#     credentials = b64encode(b"unituser:password").decode("utf-8")
#     response = client.post(
#         "/api/v1/user/add",
#         headers={"Authorization": f"Basic {credentials}"},
#         data=new_user_data,
#         content_type="application/json",
#     )
#     assert response.status == "400 BAD REQUEST"

#     invited_user = (
#         db.session.query(models.Invite).filter_by(email=new_user_data["email"]).one_or_none()
#     )
#     assert invited_user is None
