from datetime import timedelta
import flask
import flask_mail
import unittest
import pathlib
import csv
from datetime import datetime
import typing
import pytest

from unittest import mock
from unittest.mock import MagicMock
from pyfakefs.fake_filesystem import FakeFilesystem
import freezegun

from dds_web import db
from dds_web.database import models
from dds_web.utils import current_time

from dds_web.scheduled_tasks import (
    set_available_to_expired,
    set_expired_to_archived,
    delete_invite,
    quarterly_usage,
    reporting_units_and_users,
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


def test_reporting_units_and_users(client: flask.testing.FlaskClient, fs: FakeFilesystem) -> None:
    """Test that the reporting is giving correct values."""
    # Create reporting file
    reporting_file: pathlib.Path = pathlib.Path("doc/reporting/dds-reporting.csv")
    assert not fs.exists(reporting_file)
    fs.create_file(reporting_file)
    assert fs.exists(reporting_file)

    # Rows for csv
    header: typing.List = [
        "Date",
        "Units using DDS in production",
        "Researchers",
        "Unit users",
        "Total number of users",
    ]
    first_row: typing.List = [f"2022-12-10", 2, 108, 11, 119]

    # Fill reporting file with headers and one row
    with reporting_file.open(mode="a") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)  # Header - Columns
        writer.writerow(first_row)  # First row

    time_now = datetime(year=2022, month=12, day=10, hour=10, minute=54, second=10)
    with freezegun.freeze_time(time_now):
        # Run scheduled job now
        with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
            reporting_units_and_users()
            assert mock_mail_send.call_count == 1

    # Check correct numbers
    num_units: int = models.Unit.query.count()
    num_users_total: int = models.User.query.count()
    num_unit_users: int = models.UnitUser.query.count()
    num_researchers: int = models.ResearchUser.query.count()
    num_superadmins: int = models.SuperAdmin.query.count()
    num_users_excl_superadmins: int = num_users_total - num_superadmins

    # Expected new row:
    new_row: typing.List = [
        f"{time_now.year}-{time_now.month}-{time_now.day}",
        num_units,
        num_researchers,
        num_unit_users,
        num_users_excl_superadmins,
    ]

    # Check csv file contents
    with reporting_file.open(mode="r") as result:
        reader = csv.reader(result)
        line: int = 0
        for row in reader:
            if line == 0:
                assert row == header
            elif line == 1:
                assert row == [str(x) for x in first_row]
            elif line == 2:
                assert row == [str(x) for x in new_row]
            line += 1

    # Delete file to test error
    fs.remove(reporting_file)
    assert not fs.exists(reporting_file)

    # Test no file found
    with freezegun.freeze_time(time_now):
        # Run scheduled job now
        with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
            with pytest.raises(Exception) as err:
                reporting_units_and_users()
                assert mock_mail_send.call_count == 1
            assert str(err.value) == "Could not find the csv file."

    # Change total number of users to test error
    with unittest.mock.patch("dds_web.scheduled_tasks.sum") as mocker:
        mocker.return_value = num_users_total + 1
        # Test incorrect number of users
        with freezegun.freeze_time(time_now):
            # Run scheduled job now
            with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
                with pytest.raises(Exception) as err:
                    reporting_units_and_users()
                    assert mock_mail_send.call_count == 1
                assert str(err.value) == "Sum of number of users incorrect."
