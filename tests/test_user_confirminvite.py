# import json
# import tests
# import flask
# from dds_web import db
# from dds_web.database import models
# import itsdangerous


# def get_email_token(email):
#     s = itsdangerous.URLSafeTimedSerializer(flask.current_app.config["SECRET_KEY"])
#     token = s.dumps(email, salt="email-confirm")

#     return token


# def test_no_token(client):
#     response = client.get(tests.DDSEndpoint.USER_CONFIRM, content_type="application/json")
#     assert response.status == "404 NOT FOUND"


# def test_invalid_token(client):
#     response = client.get(
#         tests.DDSEndpoint.USER_CONFIRM + "invalidtokentesting",
#         content_type="application/json",
#     )
#     assert response.status == "400 BAD REQUEST"


# def test_expired_token(client):
#     response = client.get(
#         tests.DDSEndpoint.USER_CONFIRM
#         + "ImZpcnN0X3Rlc3RfZW1haWxAbWFpbHRyYXAuaW8i.YW2HiQ.zT4zcM-yt_5S6NfCn2VoYDQSv_g",
#         content_type="application/json",
#     )
#     assert response.status == "400 BAD REQUEST"


# def test_valid_token(client):
#     invite = (
#         db.session.query(models.Invite)
#         .filter_by(email="existing_invite_email@mailtrap.io", role="Researcher")
#         .one_or_none()
#     )
#     assert invite

#     token = get_email_token(email=invite.email)
#     assert token

#     response = client.get(tests.DDSEndpoint.USER_CONFIRM + token, content_type="application/json")
#     assert response.status == "200 OK"
#     assert b"Registration form" in response.data
