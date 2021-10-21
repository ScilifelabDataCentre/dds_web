# import json
# from dds_web import db
# from dds_web.database import models
# import tests

# first_new_email = {"email": "first_test_email@mailtrap.io"}
# first_new_user = {**first_new_email, "role": "Researcher"}
# first_new_user_extra_args = {**first_new_user, "extra": "test"}
# first_new_user_invalid_role = {**first_new_email, "role": "Invalid Role"}
# first_new_user_invalid_email = {"email": "first_invalid_email", "role": first_new_user["role"]}
# existing_invite = {"email": "existing_invite_email@mailtrap.io", "role": "Researcher"}
# new_unit_admin = {"email": "new_unit_admin@mailtrap.io", "role": "Super Admin"}


# def test_add_user_with_researcher(client):
#     response = client.post(
#         tests.DDSEndpoint.USER_ADD,
#         headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).post_headers(),
#         data=json.dumps(first_new_user),
#         content_type="application/json",
#     )
#     assert response.status == "403 FORBIDDEN"
#     invited_user = (
#         db.session.query(models.Invite).filter_by(email=first_new_user["email"]).one_or_none()
#     )
#     assert invited_user is None


# def test_add_user_with_unituser_no_role(client):
#     response = client.post(
#         tests.DDSEndpoint.USER_ADD,
#         headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
#         data=json.dumps(first_new_email),
#         content_type="application/json",
#     )
#     assert response.status == "400 BAD REQUEST"
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
#     assert response.status == "400 BAD REQUEST"
#     invited_user = (
#         db.session.query(models.Invite)
#         .filter_by(email=first_new_user_extra_args["email"])
#         .one_or_none()
#     )
#     assert invited_user is None


# def test_add_user_with_unitadmin_and_invalid_role(client):
#     response = client.post(
#         tests.DDSEndpoint.USER_ADD,
#         headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
#         data=json.dumps(first_new_user_invalid_role),
#         content_type="application/json",
#     )
#     assert response.status == "400 BAD REQUEST"
#     invited_user = (
#         db.session.query(models.Invite)
#         .filter_by(email=first_new_user_invalid_role["email"])
#         .one_or_none()
#     )
#     assert invited_user is None


# def test_add_user_with_unitadmin_and_invalid_email(client):
#     response = client.post(
#         tests.DDSEndpoint.USER_ADD,
#         headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
#         data=json.dumps(first_new_user_invalid_email),
#         content_type="application/json",
#     )
#     assert response.status == "400 BAD REQUEST"
#     invited_user = (
#         db.session.query(models.Invite)
#         .filter_by(email=first_new_user_invalid_email["email"])
#         .one_or_none()
#     )
#     assert invited_user is None


# def test_add_user_with_unitadmin(client):
#     response = client.post(
#         tests.DDSEndpoint.USER_ADD,
#         headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
#         data=json.dumps(first_new_user),
#         content_type="application/json",
#     )
#     assert response.status == "200 OK"

#     invited_user = (
#         db.session.query(models.Invite).filter_by(email=first_new_user["email"]).one_or_none()
#     )
#     assert invited_user
#     assert invited_user.email == first_new_user["email"]
#     assert invited_user.role == first_new_user["role"]


# def test_add_user_existing_email(client):
#     invited_user = (
#         db.session.query(models.Invite)
#         .filter_by(email=existing_invite["email"], role=existing_invite["role"])
#         .one_or_none()
#     )
#     assert invited_user
#     response = client.post(
#         tests.DDSEndpoint.USER_ADD,
#         headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
#         data=json.dumps(existing_invite),
#         content_type="application/json",
#     )
#     assert response.status == "400 BAD REQUEST"


# def test_add_user_with_unitpersonnel_permission_denied(client):
#     response = client.post(
#         tests.DDSEndpoint.USER_ADD,
#         headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).post_headers(),
#         data=json.dumps(new_unit_admin),
#         content_type="application/json",
#     )
#     assert response.status == "403 FORBIDDEN"

#     invited_user = (
#         db.session.query(models.Invite).filter_by(email=new_unit_admin["email"]).one_or_none()
#     )
#     assert invited_user is None
