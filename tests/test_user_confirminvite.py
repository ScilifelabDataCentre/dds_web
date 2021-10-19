import json
import tests


def test_no_token(client):
    response = client.get(tests.DDSEndpoint.USER_CONFIRM, content_type="application/json")
    assert response.status == "404 NOT FOUND"


def test_invalid_token(client):
    response = client.get(
        tests.DDSEndpoint.USER_CONFIRM + "invalidtokentesting",
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"


def test_expired_token(client):
    response = client.get(
        tests.DDSEndpoint.USER_CONFIRM
        + "ImZpcnN0X3Rlc3RfZW1haWxAbWFpbHRyYXAuaW8i.YW2HiQ.zT4zcM-yt_5S6NfCn2VoYDQSv_g",
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"
