from datetime import timedelta

import flask

from unittest import mock
from unittest.mock import MagicMock

from dds_web import db
from dds_web.database import models
from dds_web.utils import current_time

from dds_web.scheduled_tasks import (
    set_available_to_expired,
    set_expired_to_archived,
    delete_invite,
    quarterly_usage,
)

from typing import List

# set_available_to_expired


def test_set_available_to_expired(client: flask.testing.FlaskClient) -> None:
    units: List = db.session.query(models.Unit).all()
    # Set project statuses to Available
    # and deadline to now to be able to test cronjob functionality
    for unit in units:
        for project in unit.projects:
            for status in project.project_statuses:
                status.deadline = current_time() - timedelta(weeks=1)
                status.status = "Available"

    i: int = 0
    for unit in units:
        i += len(
            [
                project
                for project in unit.projects
                if project.current_status == "Available"
                and project.current_deadline <= current_time()
            ]
        )
    assert i == 6

    set_available_to_expired()

    units: List = db.session.query(models.Unit).all()

    i: int = 0
    j: int = 0
    for unit in units:
        i += len([project for project in unit.projects if project.current_status == "Available"])
        j += len([project for project in unit.projects if project.current_status == "Expired"])

    assert i == 0
    assert j == 6


# set_expired_to_archived


@mock.patch("boto3.session.Session")
def test_set_expired_to_archived(_: MagicMock, client: flask.testing.FlaskClient) -> None:
    units: List = db.session.query(models.Unit).all()

    for unit in units:
        for project in unit.projects:
            for status in project.project_statuses:
                status.deadline = current_time() - timedelta(weeks=1)
                status.status = "Expired"

    i: int = 0
    for unit in units:
        i += len([project for project in unit.projects if project.current_status == "Expired"])
    assert i == 6

    set_expired_to_archived()

    units: List = db.session.query(models.Unit).all()

    i: int = 0
    j: int = 0
    for unit in units:
        i += len([project for project in unit.projects if project.current_status == "Expired"])
        j += len([project for project in unit.projects if project.current_status == "Archived"])

    assert i == 0
    assert j == 6


def test_delete_invite(client: flask.testing.FlaskClient) -> None:
    assert len(db.session.query(models.Invite).all()) == 2
    delete_invite()
    assert len(db.session.query(models.Invite).all()) == 1


def test_delete_invite_timestamp_issue(client: flask.testing.FlaskClient) -> None:
    """Test that the delete_invite cronjob deletes invites with '0000-00-00 00:00:00' timestamp."""
    assert len(db.session.query(models.Invite).all()) == 2
    invites = db.session.query(models.Invite).all()
    for invite in invites:
        invite.created_at = "0000-00-00 00:00:00"
    db.session.commit()
    delete_invite()
    assert len(db.session.query(models.Invite).all()) == 0


def test_quarterly_usage(client: flask.testing.FlaskClient) -> None:
    """Test the quarterly_usage cron job."""
    quarterly_usage()
