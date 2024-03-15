# Standard libraries
import http
import unittest

# Installed
import flask
import flask_mail
import itsdangerous
import pytest
import sqlalchemy
from unittest.mock import patch, MagicMock

# own modules
import dds_web.utils
import dds_web.errors as ddserr
import tests


from dds_web import db
from dds_web.database import models
from dds_web.api import db_tools
from dds_web.errors import UserDeletionError, DatabaseError


def test_remove_user_self_deletion_request_no_request(client):

    user = models.User.query.get("researchuser2")
    assert user

    # Mock the database session
    mock_session = MagicMock()
    mock_session.delete = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.rollback = MagicMock()

    mock_models = MagicMock()
    mock_models.DeletionRequest.query.filter.return_value.one_or_none.return_value = None

    with patch("dds_web.db.session", mock_session), patch(
        "dds_web.api.db_tools.models", mock_models
    ):
        # Call the function to remove the deletion request
        with pytest.raises(UserDeletionError):
            db_tools.remove_user_self_deletion_request(user)

        # Check that the deletion request was not removed from the database
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()


def test_remove_user_self_deletion_request_database_error(client):

    user = models.User.query.get("delete_me_researcher")
    assert user

    # Mock the database session and exceptions
    mock_session = MagicMock()
    mock_session.delete = MagicMock(side_effect=sqlalchemy.exc.SQLAlchemyError("Database error"))
    mock_session.commit = MagicMock()
    mock_session.rollback = MagicMock()

    with patch("dds_web.db.session", mock_session):
        # Call the function to remove the deletion request
        with pytest.raises(DatabaseError):
            db_tools.remove_user_self_deletion_request(user)

        # Check that the deletion request was not removed from the database
        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_called_once()
        # Deletion request still exists
        del_req = models.DeletionRequest.query.filter_by(
            email="delete_me_researcher@mailtrap.io"
        ).one_or_none()

        assert del_req is not None
