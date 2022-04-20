from datetime import timedelta

import flask

import tests
import unittest
from unittest import mock
from unittest.mock import MagicMock

from dds_web import db
from dds_web.database import models
from dds_web.utils import current_time

from dds_web.scheduled_tasks import set_available_to_expired, set_expired_to_archived, delete_invite


def test_set_available_to_expired(client: flask.testing.FlaskClient) -> None:
    units: List = db.session.query(models.Unit).all()
    # Set project statuses to Available
    # and deadline to now to be able to test cronjob functionality
    for unit in units:
        for project in unit.projects:
            for status in project.project_statuses:
                status.deadline = current_time() - timedelta(weeks=1)
                status.status = "Available"

    i: Int = 0
    for unit in units:
        for project in unit.projects:
            assert len(project.project_statuses) == 1
            for status in project.project_statuses:
                if status.status == "Available" and project.current_deadline <= current_time():
                    i += 1
                assert (
                    status.status == "In Progress"
                    or status.status == "Available"
                    or status.status == "Expired"
                )
    assert i == 5

    set_available_to_expired()

    units: List = db.session.query(models.Unit).all()

    for unit in units:
        for project in unit.projects:
            j: Int = 0
            for status in project.project_statuses:
                if status.status == "Expired":
                    j += 1
            assert j == 1


@mock.patch("boto3.session.Session")
def test_set_expired_to_archived(_: MagicMock, client: flask.testing.FlaskClient) -> None:
    units: List = db.session.query(models.Unit).all()

    for unit in units:
        for project in unit.projects:
            for status in project.project_statuses:
                status.deadline = current_time() - timedelta(weeks=1)
                status.status = "Expired"

    i: Int = 0
    for unit in units:
        for project in unit.projects:
            assert len(project.project_statuses) == 1
            for status in project.project_statuses:
                if status.status == "Expired":
                    i += 1
                assert status.status == "Expired"
    assert i == 5

    set_expired_to_archived()

    units: List = db.session.query(models.Unit).all()

    i: Int = 0
    for unit in units:
        for project in unit.projects:
            assert len(project.project_statuses) == 2
            for status in project.project_statuses:
                if status.status == "Archived":
                    i += 1
                assert status.status == "Archived" or status.status == "Expired"
    assert i == 5


def test_delete_invite(client: flask.testing.FlaskClient) -> None:
    assert len(db.session.query(models.Invite).all()) == 2
    delete_invite()
    assert len(db.session.query(models.Invite).all()) == 1
