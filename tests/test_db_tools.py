# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import json
import pytest
import marshmallow
import unittest

# Installed
from dds_web import db

# Own
from dds_web.database import models
from dds_web.utils import current_time
import tests
from dds_web.api import db_tools
from dds_web.errors import DDSArgumentError, NoSuchProjectError, UserDeletionError

# TESTS #################################################################################### TESTS #

# Test remove_user_self_deletion_request


def test_remove_user_self_deletion_request_none(client):
    """Remove the row in DeletionRequest table."""
    non_user = None
    with pytest.raises(UserDeletionError) as err:
        db_tools.remove_user_self_deletion_request(user=non_user)
    assert "User object needed to get deletion request." in str(err.value)


def test_remove_user_self_deletion_request_no_request(client):
    """Attempt to remove a request for a user which haven't requested deletion."""
    user = models.User.query.first()
    with pytest.raises(UserDeletionError) as err:
        db_tools.remove_user_self_deletion_request(user=user)
    assert "There is no deletion request from this user."


def test_remove_user_self_deletion_request_success(client):
    """Remove a deletion request."""
    # Create DeletionRequest
    user = models.User.query.first()
    new_deletion_request = models.DeletionRequest(
        email=user.primary_email, issued=current_time(), requester=user
    )
    db.session.add(new_deletion_request)
    db.session.commit()

    # Verify DeletionRequest exists
    assert models.DeletionRequest.query.filter_by(requester_id=user.username).one()

    # Try deleting
    email = db_tools.remove_user_self_deletion_request(user=user)
    assert email

    # Verify it's deleted
    assert not models.DeletionRequest.query.filter_by(requester_id=user.username).all()


# Test get_project_object


def test_get_project_object_none(client):
    """Get project object when project_id is None."""
    for choice in [True, False]:
        with pytest.raises(DDSArgumentError) as err:
            db_tools.get_project_object(project_id=None, for_update=choice)
        assert "Project ID required." in str(err.value)


def test_get_project_object_no_such_project(client):
    """Get project object when project does not exist."""
    for choice in [True, False]:
        with pytest.raises(NoSuchProjectError) as err:
            db_tools.get_project_object(project_id="non_existent_project", for_update=choice)
        assert "The specified project does not exist." in str(err.value)


def test_get_project_object_existing_project(client):
    for choice in [True, False]:
        project = models.Project.query.first()
        project_id = project.public_id
        project_object = db_tools.get_project_object(project_id=project_id, for_update=choice)
        assert project_object and project_object == project
