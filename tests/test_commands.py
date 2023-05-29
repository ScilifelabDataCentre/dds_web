# Imports

# Standard
import typing
from unittest import mock
from unittest.mock import patch
from unittest.mock import PropertyMock
from unittest.mock import MagicMock
import os
import pytest
from _pytest.logging import LogCaptureFixture
import logging
from datetime import datetime, timedelta
import pathlib
import csv

# Installed
import click
from pyfakefs.fake_filesystem import FakeFilesystem
import flask_mail
import freezegun

# Own
from dds_web.commands import (
    fill_db_wrapper,
    create_new_unit,
    update_uploaded_file_with_log,
    monitor_usage,
    set_available_to_expired,
    set_expired_to_archived,
    delete_invites,
    quarterly_usage,
    collect_stats,
)
from dds_web.database import models
from dds_web import db
from dds_web.utils import current_time

# Tools


def mock_commit():
    return


def mock_no_project():
    return None


def mock_unit_size():
    return 100


# fill_db_wrapper


def test_fill_db_wrapper_production(client, runner) -> None:
    """Run init-db with the production argument."""
    result: click.testing.Result = runner.invoke(fill_db_wrapper, ["production"])
    assert result.exit_code == 1


def test_fill_db_wrapper_devsmall(client, runner) -> None:
    """Run init-db with the dev-small argument."""
    result: click.testing.Result = runner.invoke(fill_db_wrapper, ["dev-small"])
    assert result.exit_code == 1


# def test_fill_db_wrapper_devbig(client, runner) -> None:
#     """Run init-db with the dev-big argument."""
#     result: click.testing.Result = runner.invoke(fill_db_wrapper, ["dev-big"])
#     assert result.exit_code == 1

# create_new_unit


def create_command_options_from_dict(options: typing.Dict) -> typing.List:
    """Create a list with options and values from a dict."""
    # Create command options
    command_options: typing.List = []
    for key, val in options.items():
        command_options.append(f"--{key}")
        command_options.append(val)

    return command_options


correct_unit: typing.Dict = {
    "name": "newname",
    "public_id": "newpublicid",
    "external_display_name": "newexternaldisplay",
    "contact_email": "newcontact@mail.com",
    "internal_ref": "newinternalref",
    "safespring_endpoint": "newsafespringendpoint",
    "safespring_name": "newsafespringname",
    "safespring_access": "newsafespringaccess",
    "safespring_secret": "newsafespringsecret",
    "days_in_available": 45,
    "days_in_expired": 15,
}


def test_create_new_unit_public_id_too_long(client, runner) -> None:
    """Create new unit, public_id too long."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "public" * 10

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' can be a maximum of 50 characters" in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_incorrect_characters(client, runner) -> None:
    """Create new unit, public_id has invalid characters (here _)."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "new_public_id"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' can only contain letters, numbers, dots (.) and hyphens (-)." in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_starts_with_dot(client, runner) -> None:
    """Create new unit, public_id starts with invalid character (. or -)."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = ".newpublicid"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' must begin with a letter or number." in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )

    # Change public_id again
    incorrect_unit["public_id"] = "-newpublicid"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' must begin with a letter or number." in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_too_many_dots(client, runner) -> None:
    """Create new unit, public_id has invalid number of dots."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "new.public..id"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' should not contain more than two dots." in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_invalid_start(client, runner) -> None:
    """Create new unit, public_id starts with prefix."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "xn--newpublicid"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' cannot begin with the 'xn--' prefix." in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_success(client, runner) -> None:
    """Create new unit, public_id starts with prefix."""
    # Get command options
    command_options = create_command_options_from_dict(options=correct_unit)

    with patch("dds_web.db.session.commit", mock_commit):
        # Run command
        result: click.testing.Result = runner.invoke(create_new_unit, command_options)
        # assert f"Unit '{correct_unit['name']}' created" in result.output


# update_uploaded_file_with_log


def test_update_uploaded_file_with_log_nonexisting_project(client, runner) -> None:
    """Add file info to non existing project."""
    # Create command options
    command_options: typing.List = [
        "--project",
        "projectdoesntexist",
        "--path-to-log-file",
        "somefile",
    ]

    # Run command
    assert db.session.query(models.Project).all()
    with patch("dds_web.database.models.Project.query.filter_by", mock_no_project):
        result: click.testing.Result = runner.invoke(update_uploaded_file_with_log, command_options)
        assert result.exit_code == 1


def test_update_uploaded_file_with_log_nonexisting_file(client, runner, fs: FakeFilesystem) -> None:
    """Attempt to read file which does not exist."""
    # Verify that fake file does not exist
    non_existent_log_file: str = "this_is_not_a_file.json"
    assert not os.path.exists(non_existent_log_file)

    # Create command options
    command_options: typing.List = [
        "--project",
        "projectdoesntexist",
        "--path-to-log-file",
        non_existent_log_file,
    ]

    # Run command
    result: click.testing.Result = runner.invoke(update_uploaded_file_with_log, command_options)
    assert result.exit_code == 1


# monitor_usage


# usage = 0 --> check log
def test_monitor_usage_no_usage(client, cli_runner, capfd):
    """If a unit has no uploaded data, there's no need to do the calculations or send email warning."""
    # Mock the size property of the Unit table
    with patch("dds_web.database.models.Unit.size", new_callable=PropertyMock) as mock_size:
        mock_size.return_value = 0  # Test size = 0
        # Mock emails - only check if function call
        with patch.object(flask_mail.Mail, "send") as mock_mail_send:
            # Run command
            _: click.testing.Result = cli_runner.invoke(monitor_usage)
            # Verify no email has been sent and stoud contains logging info
            assert mock_mail_send.call_count == 0
    # Logging ends up in stderr
    _, err = capfd.readouterr()
    for unit in models.Unit.query.all():
        assert f"{unit.name} usage: 0 bytes. Skipping percentage calculation." in err


# percentage below warning level --> check log + no email
def test_monitor_usage_no_email(client, cli_runner, capfd):
    """No email should be sent if the usage is below the warning level."""
    # Define quota
    quota_in_test: int = 1e14
    assert quota_in_test == 100000000000000
    for unit in models.Unit.query.all():
        unit.quota = quota_in_test
        unit.warning_level = 0.8
    db.session.commit()

    # Mock the size property of the Unit table
    with patch("dds_web.database.models.Unit.size", new_callable=PropertyMock) as mock_size:
        mock_size.return_value = 0.7 * quota_in_test
        # Mock emails - only check if function call
        with patch.object(flask_mail.Mail, "send") as mock_mail_send:
            # Run command
            _: click.testing.Result = cli_runner.invoke(monitor_usage)
            # Verify no email has been sent and stoud contains logging info
            assert mock_mail_send.call_count == 0
    # Logging ends up in stderr
    _, err = capfd.readouterr()
    for unit in models.Unit.query.all():
        assert f"Monitoring the usage for unit '{unit.name}' showed the following:\n" in err
        assert (
            f"A SciLifeLab Unit is approaching the allocated data quota.\nAffected unit: {unit.name}\n"
            not in err
        )


# percentage above warning level --> check log + email sent
def test_monitor_usage_warning_sent(client, cli_runner, capfd):
    """An email should be sent if the usage is above the warning level."""
    # Define quota
    quota_in_test: int = 1e14
    assert quota_in_test == 100000000000000
    for unit in models.Unit.query.all():
        unit.quota = quota_in_test
        unit.warning_level = 0.8
    db.session.commit()

    # Mock the size property of the Unit table
    with patch("dds_web.database.models.Unit.size", new_callable=PropertyMock) as mock_size:
        mock_size.return_value = 0.9 * quota_in_test
        # Mock emails - only check if function call
        with patch.object(flask_mail.Mail, "send") as mock_mail_send:
            # Run command
            _: click.testing.Result = cli_runner.invoke(monitor_usage)
            # Verify no email has been sent and stoud contains logging info
            assert mock_mail_send.call_count == 2  # 2 because client and cli_runner both run

    _, err = capfd.readouterr()
    for unit in models.Unit.query.all():
        assert (
            f"A SciLifeLab Unit is approaching the allocated data quota.\nAffected unit: {unit.name}\n"
            in err
        )


# set_available_to_expired


def test_set_available_to_expired(client, cli_runner):
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

    cli_runner.invoke(set_available_to_expired)

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
def test_set_expired_to_archived(_: MagicMock, client, cli_runner):
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

    cli_runner.invoke(set_expired_to_archived)

    units: List = db.session.query(models.Unit).all()

    i: int = 0
    j: int = 0
    for unit in units:
        i += len([project for project in unit.projects if project.current_status == "Expired"])
        j += len([project for project in unit.projects if project.current_status == "Archived"])

    assert i == 0
    assert j == 6


# delete invites


def test_delete_invite(client, cli_runner):
    assert len(db.session.query(models.Invite).all()) == 2
    cli_runner.invoke(delete_invites)
    assert len(db.session.query(models.Invite).all()) == 1


def test_delete_invite_timestamp_issue(client, cli_runner):
    """Test that the delete_invite cronjob deletes invites with '0000-00-00 00:00:00' timestamp."""
    assert len(db.session.query(models.Invite).all()) == 2
    invites = db.session.query(models.Invite).all()
    for invite in invites:
        invite.created_at = "0000-00-00 00:00:00"
    db.session.commit()
    cli_runner.invoke(delete_invites)
    assert len(db.session.query(models.Invite).all()) == 0


# quarterly usage


def test_quarterly_usage(client, cli_runner):
    """Test the quarterly_usage cron job."""
    cli_runner.invoke(quarterly_usage)


# reporting units and users


def test_collect_stats(client, cli_runner, fs: FakeFilesystem):
    """Test that the reporting is giving correct values."""
    from dds_web.database.models import Unit, UnitUser, ResearchUser, SuperAdmin, User, Reporting

    def verify_reporting_row(row, time_date):
        """Verify correct values in reporting row."""
        assert row.date.date() == datetime.date(time_date)
        assert row.unit_count == Unit.query.count()
        assert row.researchuser_count == ResearchUser.query.count()
        assert row.unit_personnel_count == UnitUser.query.filter_by(is_admin=False).count()
        assert row.superadmin_count == SuperAdmin.query.count()
        assert row.total_user_count == User.query.count()
        assert row.total_user_count != sum(
            [row.researchuser_count, row.unit_personnel_count, row.superadmin_count]
        )

    # Verify that there are no reporting rows
    assert Reporting.query.count() == 0

    # Run successful command - new row should be created
    first_time = datetime(year=2022, month=12, day=10, hour=10, minute=54, second=10)
    with freezegun.freeze_time(first_time):
        # Run scheduled job now
        with mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
            result: click.testing.Result = cli_runner.invoke(collect_stats)
            assert not result.exception, "Raised an unwanted exception."
            assert mock_mail_send.call_count == 0

    # Verify that there's now a reporting row
    assert Reporting.query.count() == 1
    row = Reporting.query.first()
    verify_reporting_row(row=row, time_date=first_time)

    # Check that an exception is raised if the command is run on the same day
    with freezegun.freeze_time(first_time):
        # Run scheduled job now
        with mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
            # with pytest.raises(Exception) as err:
            result: click.testing.Result = cli_runner.invoke(collect_stats)
            assert result.exception, "Did not raise exception."
            assert "Duplicate entry" in str(result.exception)
            assert mock_mail_send.call_count == 1

    # Verify that the next day works
    second_time = datetime(year=2022, month=12, day=11, hour=10, minute=54, second=10)
    with freezegun.freeze_time(second_time):
        # Run scheduled job now
        with mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
            result: click.testing.Result = cli_runner.invoke(collect_stats)
            assert not result.exception, "Raised an unwanted exception."
            assert mock_mail_send.call_count == 0

    # Verify that there's now a reporting row
    assert Reporting.query.count() == 2
    reporting_rows = Reporting.query.all()
    for row in reporting_rows:
        verify_reporting_row(row=row, time_date=first_time if row.id == 1 else second_time)
