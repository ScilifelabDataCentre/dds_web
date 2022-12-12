import flask
import pytest
from unittest.mock import patch

from dds_web.api import db_tools
from dds_web.database import models
from dds_web.errors import UserDeletionError, DatabaseError
from tests.api.test_project import mock_sqlalchemyerror

def test_remove_user_self_deletion_request_no_request(client: flask.testing.FlaskClient) -> None:
    """Attempt to remove own user, without having made a request."""
    # Get user
    user: models.User = models.User.query.filter_by(username="researchuser2").first()
    assert user

    # Make sure user is not in deletion request table
    deletion_request: models.DeletionRequest = models.DeletionRequest.query.filter_by(requester_id=user.username).first()
    assert not deletion_request
    
    # Attempt deleting user with no deletion request
    with pytest.raises(UserDeletionError) as err:
        db_tools.remove_user_self_deletion_request(user=user)
    assert "There is no deletion request from this user." in str(err.value)

def test_remove_user_self_deletion_request_sqlalchemyerror(client: flask.testing.FlaskClient) -> None:
    """SQLAlchemyError when attempting to perform self deletion."""
    # Get user
    user: models.User = models.User.query.filter_by(username="researchuser").first()
    assert user

    # Make sure user is in deletionrequest
    deletion_request: models.DeletionRequest = models.DeletionRequest.query.filter_by(requester_id=user.username).first()
    assert deletion_request
    
    # Attempt deleting user
    with pytest.raises(DatabaseError) as err:
        with patch("dds_web.db.session.commit", mock_sqlalchemyerror):
            db_tools.remove_user_self_deletion_request(user=user)
    assert "Failed to remove deletion request" in str(err.value)

    # Verify that request not deleted
    deletion_request: models.DeletionRequest = models.DeletionRequest.query.filter_by(requester_id=deletion_request.requester_id).first()
    assert deletion_request

def test_remove_user_self_deletion_request_ok(client: flask.testing.FlaskClient) -> None:
    """SQLAlchemyError when attempting to perform self deletion."""
    # Get deletion request
    deletion_request: models.DeletionRequest = models.DeletionRequest.query.first()
    assert deletion_request

    # Get user
    user: models.User = models.User.query.filter_by(username=deletion_request.requester_id).first()
    assert user

    # Delete user
    removed_email: str = db_tools.remove_user_self_deletion_request(user=user)

    # Verify that request deleted
    deletion_request: models.DeletionRequest = models.DeletionRequest.query.filter_by(requester_id=deletion_request.requester_id).first()
    assert not deletion_request