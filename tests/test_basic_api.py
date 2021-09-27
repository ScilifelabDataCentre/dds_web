from base64 import b64encode


def test_get_token_no_credentials(client):
    response = client.get("/api/v1/user/token")
    assert response.status == "401 UNAUTHORIZED"


def test_token_with_credentials(client):
    credentials = b64encode(b"username:password").decode("utf-8")
    response = client.get("/api/v1/user/token", headers={"Authorization": f"Basic {credentials}"})
    assert response.status == "200 OK"
