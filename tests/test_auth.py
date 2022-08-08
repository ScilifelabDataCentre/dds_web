import tests
import http
from dds_web.database import models
from dds_web import db

# verify_token
def test_verify_token_user_not_exists_after_deletion(client):
    """Log in, delete, log out. Should give exception."""
    # Check that user exists
    current_user: models.UnitUser = models.User.query.get("unituser")
    assert current_user

    # Authenticate
    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)

    # Verify that user has access from beginning
    response = client.get(
        tests.DDSEndpoint.LIST_FILES, headers=token, query_string={"project": "public_project_id"}
    )
    assert response.status_code == http.HTTPStatus.OK

    # Delete user
    db.session.delete(current_user)
    db.session.commit()

    # Check that user dot not exist
    current_user: models.UnitUser = models.User.query.get("unituser")
    assert not current_user

    # Attempt run
    response = client.get(tests.DDSEndpoint.LIST_FILES, headers=token)
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # Verify message
    response_json = response.json
    message = response_json.get("message")
    assert message == "Invalid token. Try reauthenticating."
