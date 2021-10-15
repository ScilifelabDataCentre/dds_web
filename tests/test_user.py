from base64 import b64encode
import json
from dds_web import db

new_user_data = {"email": "first_email@mailtrap.io"}


def test_add_user_without_credentials(client):
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
