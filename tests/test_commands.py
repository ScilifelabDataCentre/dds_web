# Imports

# Standard
import typing
from unittest import mock
from unittest.mock import patch, mock_open
from unittest.mock import PropertyMock
from unittest.mock import MagicMock
import os
import pytest
from _pytest.logging import LogCaptureFixture
import logging
from datetime import datetime, timedelta
import pathlib
import csv
from dateutil.relativedelta import relativedelta
import json

# Installed
import click
from pyfakefs.fake_filesystem import FakeFilesystem
import flask_mail
import freezegun
import rich.prompt
import sqlalchemy

# Own
from dds_web.commands import (
    fill_db_wrapper,
    create_new_unit,
    update_uploaded_file_with_log,
    monitor_usage,
    set_available_to_expired,
    set_expired_to_archived,
    delete_invites,
    monthly_usage,
    collect_stats,
    lost_files_s3_db,
    update_unit_sto4,
    update_unit_quota,
    send_usage,
    restart_redis_worker,
)
from dds_web.database import models
from dds_web import db, mail
from dds_web.utils import current_time

# Tools


def mock_commit():
    return


def mock_no_project():
    return None


def mock_unit_size():
    return 100


# fill_db_wrapper


def test_fill_db_wrapper_production(client, runner, capfd: LogCaptureFixture) -> None:
    """Run init-db with the production argument."""
    _: click.testing.Result = runner.invoke(fill_db_wrapper, ["production"])
    _, err = capfd.readouterr()
    assert "already exists, not creating user" in err


def test_fill_db_wrapper_devsmall(client, runner, capfd: LogCaptureFixture) -> None:
    """Run init-db with the dev-small argument."""
    _: click.testing.Result = runner.invoke(fill_db_wrapper, ["dev-small"])
    _, err = capfd.readouterr()
    assert "Initializing development db" in err
    assert "DB filled" not in err  # DB already filled, duplicates.


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
    "quota": 80,
}


def test_create_new_unit_public_id_too_long(client, runner, capfd: LogCaptureFixture) -> None:
    """Create new unit, public_id too long."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "public" * 10

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    _: click.testing.Result = runner.invoke(create_new_unit, command_options)

    # Get log output
    _, err = capfd.readouterr()
    assert "The 'public_id' can be a maximum of 50 characters" in err

    # Verify that unit doesn't exist
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_incorrect_warning_level(client, runner, capfd: LogCaptureFixture) -> None:
    """Create new unit, warning level is not a float between 0.0 and 1.0"""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["warn-at"] = 30

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)

    assert result.exit_code != 0  # No sucess
    # Verify that unit doesn't exist
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_incorrect_characters(
    client, runner, capfd: LogCaptureFixture
) -> None:
    """Create new unit, public_id has invalid characters (here _)."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "new_public_id"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    _: click.testing.Result = runner.invoke(create_new_unit, command_options)

    # Get log output_
    _, err = capfd.readouterr()
    assert "The 'public_id' can only contain letters, numbers, dots (.) and hyphens (-)." in err

    # Verify that unit doesn't exist
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_starts_with_dot(
    client, runner, capfd: LogCaptureFixture
) -> None:
    """Create new unit, public_id starts with invalid character (. or -)."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = ".newpublicid"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    _: click.testing.Result = runner.invoke(create_new_unit, command_options)

    # Get log output
    _, err = capfd.readouterr()
    assert "The 'public_id' must begin with a letter or number." in err

    # Verify that the unit doesn't exist
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )

    # Change public_id again
    incorrect_unit["public_id"] = "-newpublicid"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    _: click.testing.Result = runner.invoke(create_new_unit, command_options)

    # Get log output
    _, err = capfd.readouterr()
    assert "The 'public_id' must begin with a letter or number." in err

    # Verify that the unit doesn't exist
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_too_many_dots(client, runner, capfd: LogCaptureFixture) -> None:
    """Create new unit, public_id has invalid number of dots."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "new.public..id"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    _: click.testing.Result = runner.invoke(create_new_unit, command_options)

    # Get log output
    _, err = capfd.readouterr()
    assert "The 'public_id' should not contain more than two dots." in err

    # Verify that the unit doesn't exist
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_invalid_start(client, runner, capfd: LogCaptureFixture) -> None:
    """Create new unit, public_id starts with prefix."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "xn--newpublicid"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    _: click.testing.Result = runner.invoke(create_new_unit, command_options)

    # Get log output
    _, err = capfd.readouterr()
    assert "The 'public_id' cannot begin with the 'xn--' prefix." in err

    # Verify that the unit doesn't exist
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_success(client, runner, capfd: LogCaptureFixture) -> None:
    """Create new unit, public_id starts with prefix."""
    # Get command options
    command_options = create_command_options_from_dict(options=correct_unit)

    with patch("dds_web.db.session.commit", mock_commit):
        # Run command
        _: click.testing.Result = runner.invoke(create_new_unit, command_options)

    _, err = capfd.readouterr()
    assert f"Unit '{correct_unit['name']}' created" in err

    new_unit = (
        db.session.query(models.Unit).filter(models.Unit.name == correct_unit["name"]).one_or_none()
    )

    # Check that the different attributes have been set up

    assert new_unit.public_id == correct_unit["public_id"]
    assert new_unit.external_display_name == correct_unit["external_display_name"]
    assert new_unit.contact_email == correct_unit["contact_email"]
    assert new_unit.internal_ref
    assert new_unit.sto4_start_time
    assert new_unit.sto4_endpoint == correct_unit["safespring_endpoint"]
    assert new_unit.sto4_name == correct_unit["safespring_name"]
    assert new_unit.sto4_access == correct_unit["safespring_access"]
    assert new_unit.sto4_secret == correct_unit["safespring_secret"]
    assert new_unit.days_in_available
    assert new_unit.days_in_expired
    assert new_unit.quota == correct_unit["quota"]
    assert new_unit.warning_level


# update_unit_sto4


def test_update_unit_sto4_no_such_unit(client, runner, capfd: LogCaptureFixture) -> None:
    """Try to update a non existent unit -> Error."""
    # Create command options
    command_options: typing.List = [
        "--unit-id",
        "unitdoesntexist",
        "--sto4-endpoint",
        "endpoint_sto4",
        "--sto4-name",
        "name_sto4",
        "--sto4-access",
        "access_sto4",
        "--sto4-secret",
        "secret_sto4",
    ]

    # Run command
    result: click.testing.Result = runner.invoke(update_unit_sto4, command_options)
    assert result.exit_code == 0
    assert not result.output

    # Get logging
    _, err = capfd.readouterr()

    # Verify message
    assert f"There is no unit with the public ID '{command_options[1]}'." in err


def test_update_unit_sto4_start_time_exists_mock_prompt_False(
    client, runner, capfd: LogCaptureFixture
) -> None:
    """Start time already recorded. Answer no to prompt about update anyway. No changes should be made."""
    # Get existing unit
    unit: models.Unit = models.Unit.query.first()
    unit_id: str = unit.public_id

    # Get sto4 info from start
    sto4_endpoint_original = unit.sto4_endpoint
    sto4_name_original = unit.sto4_name
    sto4_access_original = unit.sto4_access
    sto4_secret_original = unit.sto4_secret
    sto4_info_original = [
        sto4_endpoint_original,
        sto4_name_original,
        sto4_access_original,
        sto4_secret_original,
    ]
    assert sto4_info_original == [None, None, None, None]

    # Set sto4 start time
    unit.sto4_start_time = current_time()
    db.session.commit()

    # Create command options
    command_options: typing.List = [
        "--unit-id",
        unit_id,
        "--sto4-endpoint",
        "endpoint_sto4",
        "--sto4-name",
        "name_sto4",
        "--sto4-access",
        "access_sto4",
        "--sto4-secret",
        "secret_sto4",
    ]

    # Run command
    # Mock rich prompt - False
    with patch.object(rich.prompt.Confirm, "ask", return_value=False) as mock_ask:
        result: click.testing.Result = runner.invoke(update_unit_sto4, command_options)
        assert result.exit_code == 0
        assert not result.output
    mock_ask.assert_called_once

    # Get logging
    _, err = capfd.readouterr()

    # Verify logging
    assert f"Cancelling sto4 update for unit '{unit_id}'." in err
    assert f"Unit '{unit_id}' updated successfully" not in err

    # Verify no change in unit
    unit: models.Unit = models.Unit.query.filter_by(public_id=unit_id).first()
    assert unit
    assert [
        unit.sto4_endpoint,
        unit.sto4_name,
        unit.sto4_access,
        unit.sto4_secret,
    ] == sto4_info_original


def test_update_unit_sto4_start_time_exists_mock_prompt_True(
    client, runner, capfd: LogCaptureFixture
) -> None:
    """Start time already recorded. Answer yes to prompt about update anyway. Changes should be made."""
    # Get existing unit
    unit: models.Unit = models.Unit.query.first()
    unit_id: str = unit.public_id

    # Get sto4 info from start
    sto4_endpoint_original = unit.sto4_endpoint
    sto4_name_original = unit.sto4_name
    sto4_access_original = unit.sto4_access
    sto4_secret_original = unit.sto4_secret
    sto4_info_original = [
        sto4_endpoint_original,
        sto4_name_original,
        sto4_access_original,
        sto4_secret_original,
    ]
    assert sto4_info_original == [None, None, None, None]

    # Set sto4 start time
    unit.sto4_start_time = current_time()
    db.session.commit()

    # Create command options
    command_options: typing.List = [
        "--unit-id",
        unit_id,
        "--sto4-endpoint",
        "endpoint_sto4",
        "--sto4-name",
        "name_sto4",
        "--sto4-access",
        "access_sto4",
        "--sto4-secret",
        "secret_sto4",
    ]

    # Run command
    # Mock rich prompt - True
    with patch.object(rich.prompt.Confirm, "ask", return_value=True) as mock_ask:
        result: click.testing.Result = runner.invoke(update_unit_sto4, command_options)
        assert result.exit_code == 0
        assert not result.output
    mock_ask.assert_called_once

    # Get logging
    _, err = capfd.readouterr()

    # Verify logging
    assert f"Cancelling sto4 update for unit '{unit_id}'." not in err
    assert f"Unit '{unit_id}' updated successfully" in err

    # Verify change in unit
    unit: models.Unit = models.Unit.query.filter_by(public_id=unit_id).first()
    assert unit
    assert [
        unit.sto4_endpoint,
        unit.sto4_name,
        unit.sto4_access,
        unit.sto4_secret,
    ] != sto4_info_original
    assert [unit.sto4_endpoint, unit.sto4_name, unit.sto4_access, unit.sto4_secret] == [
        command_options[3],
        command_options[5],
        command_options[7],
        command_options[9],
    ]


# update_unit_quota


def test_update_unit_quota_no_such_unit(client, runner, capfd: LogCaptureFixture) -> None:
    """Try to update a non existent unit -> Error."""
    # Create command options
    command_options: typing.List = [
        "--unit-id",
        "unitdoesntexist",
        "--quota",
        2,  # 2 GB,
    ]

    # Run command
    result: click.testing.Result = runner.invoke(update_unit_quota, command_options)
    assert result.exit_code == 1
    assert not result.output

    # Get logging
    _, err = capfd.readouterr()

    # Verify message
    assert f"There is no unit with the public ID '{command_options[1]}'." in err


def test_update_unit_quota_confirm_prompt_False(client, runner, capfd: LogCaptureFixture) -> None:
    """Unit quota should not be changed when answer to prompt is False."""
    # Get existing unit
    unit: models.Unit = models.Unit.query.first()
    unit_id: str = unit.public_id

    # save original quota
    quota_original = unit.quota

    # Create command options
    command_options: typing.List = [
        "--unit-id",
        unit_id,
        "--quota",
        2,  # 2 GB,
    ]

    # Run command
    # Mock rich prompt - False
    with patch.object(rich.prompt.Confirm, "ask", return_value=False) as mock_ask:
        result: click.testing.Result = runner.invoke(update_unit_quota, command_options)
        assert result.exit_code == 0
        assert not result.output
    mock_ask.assert_called_once

    # Get logging
    _, err = capfd.readouterr()

    # Verify logging
    assert f"Cancelling quota update for unit '{unit_id}'." in err
    assert f"Unit '{unit_id}' updated successfully" not in err

    # Verify no change in unit
    unit: models.Unit = models.Unit.query.filter_by(public_id=unit_id).first()
    assert unit
    assert unit.quota == quota_original


def test_update_unit_quota_confirm_prompt_true(client, runner, capfd: LogCaptureFixture) -> None:
    """Unit quota successfully updated when answer to the prompt is True."""

    # Get existing unit
    unit: models.Unit = models.Unit.query.first()
    unit_id: str = unit.public_id

    # save original quota
    quota_original = unit.quota

    # Create command options
    command_options: typing.List = [
        "--unit-id",
        unit_id,
        "--quota",
        2,  # 2 GB,
    ]

    # Run command
    # Mock rich prompt - True
    with patch.object(rich.prompt.Confirm, "ask", return_value=True) as mock_ask:
        result: click.testing.Result = runner.invoke(update_unit_quota, command_options)
        assert result.exit_code == 0
        assert not result.output
    mock_ask.assert_called_once

    # Get logging
    _, err = capfd.readouterr()

    # Verify logging
    assert f"Cancelling quota update for unit '{unit_id}'." not in err
    assert f"Unit '{unit_id}' updated successfully" in err

    # Verify change in unit
    unit: models.Unit = models.Unit.query.filter_by(public_id=unit_id).first()
    assert unit
    assert unit.quota != quota_original
    assert unit.quota == command_options[3] * 1000**3  # GB to bytes


# update_uploaded_file_with_log


def test_update_uploaded_file_with_log_nonexisting_project(
    client, runner, capfd: LogCaptureFixture
) -> None:
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
        _: click.testing.Result = runner.invoke(update_uploaded_file_with_log, command_options)
    _, err = capfd.readouterr()
    assert "The project 'projectdoesntexist' doesn't exist." in err

    # Verify that things are not printed out
    assert "Files added:" not in err
    assert "Errors while adding files:" not in err


def test_update_uploaded_file_with_log_nonexisting_file(
    client, runner, capfd: LogCaptureFixture
) -> None:
    """Attempt to read file which does not exist."""
    # Get project
    project = models.Project.query.first()

    # Verify that fake file does not exist
    non_existent_log_file: str = "this_is_not_a_file.json"
    assert not os.path.exists(non_existent_log_file)

    # Create command options
    command_options: typing.List = [
        "--project",
        project.public_id,
        "--path-to-log-file",
        non_existent_log_file,
    ]

    # Run command
    _: click.testing.Result = runner.invoke(update_uploaded_file_with_log, command_options)

    # Check logging
    _, err = capfd.readouterr()
    assert f"The log file '{non_existent_log_file}' doesn't exist." in err

    # Verify that things are not printed out
    assert "Files added:" not in err
    assert "Errors while adding files:" not in err


def test_update_uploaded_file(client, runner, capfd: LogCaptureFixture, boto3_session) -> None:
    """Attempt to read file which does not exist."""
    # Get project
    project = models.Project.query.first()

    # # Verify that fake file exists
    log_file: str = "this_is_a_file.json"

    # Get file from db
    file_object: models.File = models.File.query.first()
    file_dict = {
        file_object.name: {
            "status": {"failed_op": "add_file_db"},
            "path_remote": file_object.name_in_bucket,
            "subpath": file_object.subpath,
            "size_raw": file_object.size_original,
            "size_processed": file_object.size_stored,
            "compressed": not file_object.compressed,
            "public_key": file_object.public_key,
            "salt": file_object.salt,
            "checksum": file_object.checksum,
        }
    }

    # Create command options
    command_options: typing.List = [
        "--project",
        project.public_id,
        "--path-to-log-file",
        log_file,
    ]
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("dds_web.commands.open"):
            with patch("json.load") as mock_json_load:
                mock_json_load.return_value = file_dict
                _: click.testing.Result = runner.invoke(
                    update_uploaded_file_with_log, command_options
                )

    # Check logging
    _, err = capfd.readouterr()
    assert f"The project '{project.public_id}' doesn't exist." not in err
    assert f"Updating file in project '{project.public_id}'..." in err
    assert f"The log file '{log_file}' doesn't exist." not in err
    assert f"Reading file info from path '{log_file}'..." in err
    assert "File contents were loaded..." in err
    assert "Files added: []" in err
    assert "Errors while adding files:" in err
    assert "File already in database" in err


# lost_files_s3_db


def test_lost_files_s3_db_no_command(client, cli_runner, capfd: LogCaptureFixture):
    """Test running the flask lost-files command without any subcommand."""
    _: click.testing.Result = cli_runner.invoke(lost_files_s3_db)
    _, err = capfd.readouterr()
    assert not err


# lost_files_s3_db -- list_lost_files


def test_list_lost_files_no_such_project(client, cli_runner, capfd: LogCaptureFixture):
    """flask lost-files ls: project specified, project doesnt exist."""
    # Project ID -- doesn't exist
    project_id: str = "nonexistentproject"
    assert not models.Project.query.filter_by(public_id=project_id).one_or_none()

    # Run command with non existent project
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["ls", "--project-id", project_id]
    )
    assert result.exit_code == 1  # sys.exit(1)

    # Verify output
    _, err = capfd.readouterr()
    assert f"Searching for lost files in project '{project_id}'." in err
    assert f"No such project: '{project_id}'" in err


def test_list_lost_files_no_lost_files_in_project(
    client, cli_runner, boto3_session, capfd: LogCaptureFixture
):
    """flask lost-files ls: project specified, no lost files."""
    # Get project
    project = models.Project.query.first()
    public_id = project.public_id
    assert project

    # Use sto2 -- no sto4_endpoint_added date ---------------------------------------------
    project_unit = project.responsible_unit
    assert not project_unit.sto4_start_time

    # Mock project.files -- no files
    with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
        mock_files.return_value = []

        # Run command
        result: click.testing.Result = cli_runner.invoke(
            lost_files_s3_db, ["ls", "--project-id", public_id]
        )
        assert result.exit_code == 0

    # Verify output -- no lost files
    _, err = capfd.readouterr()
    assert f"Safespring location for project '{public_id}': sto2" in err
    assert f"Searching for lost files in project '{public_id}'." in err
    assert f"No lost files in project '{public_id}'" in err
    # ---------------------------------------------------------------------------------------

    # Use sto2 -- sto4_endpoint_added but project created before ----------------------------
    project_unit.sto4_start_time = current_time()
    db.session.commit()

    assert project_unit.sto4_start_time
    assert project.date_created < project_unit.sto4_start_time

    # Mock project.files -- no files
    with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
        mock_files.return_value = []

        # Run command
        result: click.testing.Result = cli_runner.invoke(
            lost_files_s3_db, ["ls", "--project-id", project.public_id]
        )
        assert result.exit_code == 0

    # Verify output -- no lost files
    _, err = capfd.readouterr()
    assert f"Safespring location for project '{project.public_id}': sto2" in err
    assert f"Searching for lost files in project '{project.public_id}'." in err
    assert f"No lost files in project '{project.public_id}'" in err
    # ---------------------------------------------------------------------------------------

    # Use sto2 -- sto4_endpoint_added, project created after, but not all info is available --
    project_unit.sto4_start_time = current_time() - relativedelta(hours=1)
    db.session.commit()

    assert project_unit.sto4_start_time
    assert project.date_created > project_unit.sto4_start_time
    assert not all(
        [
            project_unit.sto4_endpoint,
            project_unit.sto4_name,
            project_unit.sto4_access,
            project_unit.sto4_secret,
        ]
    )

    # Mock project.files -- no files
    with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
        mock_files.return_value = []

        # Run command
        result: click.testing.Result = cli_runner.invoke(
            lost_files_s3_db, ["ls", "--project-id", project.public_id]
        )
        assert result.exit_code == 1

    # Verify output -- no lost files
    _, err = capfd.readouterr()
    assert f"One or more sto4 variables are missing for unit {project_unit.public_id}." in err
    assert f"Safespring location for project '{project.public_id}': sto2" not in err
    assert f"Searching for lost files in project '{project.public_id}'." in err
    assert f"No lost files in project '{project.public_id}'" not in err
    # ---------------------------------------------------------------------------------------

    # Use sto4 -- sto4_endpoint_added, project created after, and all info is available -----
    project_unit.sto4_start_time = current_time() - relativedelta(hours=1)
    project_unit.sto4_endpoint = "endpoint"
    project_unit.sto4_name = "name"
    project_unit.sto4_access = "access"
    project_unit.sto4_secret = "secret"
    db.session.commit()

    assert project_unit.sto4_start_time
    assert project.date_created > project_unit.sto4_start_time
    assert all(
        [
            project_unit.sto4_endpoint,
            project_unit.sto4_name,
            project_unit.sto4_access,
            project_unit.sto4_secret,
        ]
    )

    # Mock project.files -- no files
    with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
        mock_files.return_value = []

        # Run command
        result: click.testing.Result = cli_runner.invoke(
            lost_files_s3_db, ["ls", "--project-id", project.public_id]
        )
        assert result.exit_code == 0

    # Verify output -- no lost files
    _, err = capfd.readouterr()
    assert f"Safespring location for project '{project.public_id}': sto2" not in err
    assert f"Safespring location for project '{project.public_id}': sto4" in err
    assert f"Searching for lost files in project '{project.public_id}'." in err
    assert f"No lost files in project '{project.public_id}'" in err

    # ---------------------------------------------------------------------------------------


def test_list_lost_files_missing_in_s3_in_project(
    client, cli_runner, boto3_session, capfd: LogCaptureFixture
):
    """flask lost-files ls: project specified, lost files in s3."""
    # Get project
    project = models.Project.query.first()
    assert project

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["ls", "--project-id", project.public_id]
    )
    assert result.exit_code == 0

    # Verify output
    _, err = capfd.readouterr()
    # All files should be in db but not in s3
    for f in project.files:
        assert (
            f"Entry {f.name_in_bucket} ({project.public_id}, {project.responsible_unit}) not found in S3 (but found in db)"
            in err
        )
        assert (
            f"Entry {f.name_in_bucket} ({project.public_id}, {project.responsible_unit}) not found in database (but found in s3)"
            not in err
        )

    assert f"Lost files in project: {project.public_id}\t\tIn DB but not S3: {len(project.files)}\tIn S3 but not DB: 0\n"


def test_list_lost_files_no_lost_files_total(
    client, cli_runner, boto3_session, capfd: LogCaptureFixture
):
    """flask lost-files ls: no project specified, no lost files."""
    # Use sto2 -- no sto4_endpoint_added date ---------------------------------------------
    for u in models.Unit.query.all():
        assert not u.sto4_start_time

    # Mock project.files -- no files
    with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
        mock_files.return_value = []

        # Run command
        result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
        assert result.exit_code == 0

    # Verify output -- no lost files
    _, err = capfd.readouterr()
    assert "Searching for lost files in project" not in err
    assert "No project specified, searching for lost files in all units." in err
    for u in models.Unit.query.all():
        assert f"Listing lost files in unit: {u.public_id}" in err
        for p in u.projects:
            assert f"Safespring location for project '{p.public_id}': sto2" in err
            assert f"Safespring location for project '{p.public_id}': sto4" not in err
    assert f"No lost files for unit '{u.public_id}'" in err
    # ---------------------------------------------------------------------------------------

    # Use sto2 -- sto4_endpoint_added but project created before ----------------------------
    for u in models.Unit.query.all():
        u.sto4_start_time = current_time()
        for p in u.projects:
            assert p.date_created < u.sto4_start_time
    db.session.commit()

    # Mock project.files -- no files
    with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
        mock_files.return_value = []

        # Run command
        result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
        assert result.exit_code == 0

    # Verify output -- no lost files
    _, err = capfd.readouterr()
    assert "Searching for lost files in project" not in err
    assert "No project specified, searching for lost files in all units." in err
    for u in models.Unit.query.all():
        assert f"Listing lost files in unit: {u.public_id}" in err
        for p in u.projects:
            assert f"Safespring location for project '{p.public_id}': sto2" in err
            assert f"Safespring location for project '{p.public_id}': sto4" not in err
    assert f"No lost files for unit '{u.public_id}'" in err
    # ---------------------------------------------------------------------------------------

    # Use sto2 -- sto4_endpoint_added, project created after, but not all info is available --
    for u in models.Unit.query.all():
        u.sto4_start_time = current_time() - relativedelta(hours=1)
        for p in u.projects:
            assert p.date_created > u.sto4_start_time
    db.session.commit()

    # Mock project.files -- no files
    with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
        mock_files.return_value = []

        # Run command
        result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
        assert result.exit_code == 0

    # Verify output -- no lost files
    _, err = capfd.readouterr()
    assert "Searching for lost files in project" not in err
    assert "No project specified, searching for lost files in all units." in err
    for u in models.Unit.query.all():
        assert f"Listing lost files in unit: {u.public_id}" in err
        for p in u.projects:
            assert f"Safespring location for project '{p.public_id}': sto2" not in err
            assert f"Safespring location for project '{p.public_id}': sto4" not in err
    assert f"No lost files for unit '{u.public_id}'" in err
    # ---------------------------------------------------------------------------------------

    # Use sto4 -- sto4_endpoint_added, project created after, and all info is available -----
    for u in models.Unit.query.all():
        u.sto4_start_time = current_time() - relativedelta(hours=1)
        for p in u.projects:
            assert p.date_created > u.sto4_start_time
            u.sto4_endpoint = "endpoint"
            u.sto4_name = "name"
            u.sto4_access = "access"
            u.sto4_secret = "secret"

    db.session.commit()

    # Mock project.files -- no files
    with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
        mock_files.return_value = []

        # Run command
        result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
        assert result.exit_code == 0

    # Verify output -- no lost files
    _, err = capfd.readouterr()
    assert "Searching for lost files in project" not in err
    assert "No project specified, searching for lost files in all units." in err
    for u in models.Unit.query.all():
        assert f"Listing lost files in unit: {u.public_id}" in err
        for p in u.projects:
            assert f"Safespring location for project '{p.public_id}': sto2" not in err
            assert f"Safespring location for project '{p.public_id}': sto4" in err
    assert f"No lost files for unit '{u.public_id}'" in err
    # ---------------------------------------------------------------------------------------

    # Use sto4 for all but one --------------------------------------------------------------
    for u in models.Unit.query.all():
        u.sto4_start_time = current_time() - relativedelta(hours=1)
        for p in u.projects:
            assert p.date_created > u.sto4_start_time
            u.sto4_endpoint = "endpoint"
            u.sto4_name = "name"
            u.sto4_access = "access"
            u.sto4_secret = "secret"

    unit_no_sto4_endpoint = models.Unit.query.first()
    unit_no_sto4_endpoint_id = unit_no_sto4_endpoint.public_id
    unit_no_sto4_endpoint.sto4_endpoint = None
    db.session.commit()

    # Mock project.files -- no files
    with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
        mock_files.return_value = []

        # Run command
        result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
        assert result.exit_code == 0

    # Verify output -- no lost files
    _, err = capfd.readouterr()
    assert "Searching for lost files in project" not in err
    assert "No project specified, searching for lost files in all units." in err
    for u in models.Unit.query.all():
        assert f"Listing lost files in unit: {u.public_id}" in err
        for p in u.projects:
            if u.public_id == unit_no_sto4_endpoint_id:
                assert f"One or more sto4 variables are missing for unit {u.public_id}." in err
                assert f"Safespring location for project '{p.public_id}': sto2" not in err
                assert f"Safespring location for project '{p.public_id}': sto4" not in err
            else:
                assert f"Safespring location for project '{p.public_id}': sto2" not in err
                assert f"Safespring location for project '{p.public_id}': sto4" in err
    assert f"No lost files for unit '{u.public_id}'" in err
    # ---------------------------------------------------------------------------------------


def test_list_lost_files_missing_in_s3_in_project(
    client, cli_runner, boto3_session, capfd: LogCaptureFixture
):
    """flask lost-files ls: project specified, lost files in s3."""
    # Run command
    result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
    assert result.exit_code == 0

    # Verify output
    _, err = capfd.readouterr()
    # All files should be in db but not in s3
    for u in models.Unit.query.all():
        num_files: int = 0
        for p in u.projects:
            num_files += len(p.files)
            for f in p.files:
                assert (
                    f"Entry {f.name_in_bucket} ({p.public_id}, {u}) not found in S3 (but found in db)"
                    in err
                )
                assert (
                    f"Entry {f.name_in_bucket} ({p.public_id}, {u}) not found in database (but found in s3)"
                    not in err
                )
        assert f"Lost files for unit: {u.public_id}\t\tIn DB but not S3: {num_files}\tIn S3 but not DB: 0\tProject errors: 0\n"


# lost_files_s3_db -- add_missing_bucket


def test_add_missing_bucket_no_project(client, cli_runner):
    """flask lost-files add-missing-bucket: no project specified (required)."""
    # Run command
    result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["add-missing-bucket"])

    # Get output from result and verify that help message printed
    assert result.exit_code == 2
    assert "Missing option '--project-id' / '-p'." in result.stdout


def test_add_missing_bucket_project_nonexistent(client, cli_runner, capfd: LogCaptureFixture):
    """flask lost-files add-missing-bucket: no such project --> print out error."""
    # Project -- doesn't exist
    project_id: str = "nonexistentproject"
    assert not models.Project.query.filter_by(public_id=project_id).one_or_none()

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["add-missing-bucket", "--project-id", project_id]
    )
    assert result.exit_code == 1

    # Verify output
    _, err = capfd.readouterr()
    assert f"No such project: '{project_id}'" in err


def test_add_missing_bucket_project_inactive(client, cli_runner, capfd: LogCaptureFixture):
    """flask lost-files add-missing-bucket: project specified, but inactive --> error message."""
    # Get project
    project: models.Project = models.Project.query.first()
    assert project

    # Set project as inactive
    project.is_active = False
    db.session.commit()
    assert not project.is_active

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["add-missing-bucket", "--project-id", project.public_id]
    )
    assert result.exit_code == 1

    # Verify output
    _, err = capfd.readouterr()
    assert f"Project '{project.public_id}' is not an active project." in err


def test_add_missing_bucket_not_missing(
    client, cli_runner, boto3_session, capfd: LogCaptureFixture
):
    """flask lost-files add-missing-bucket: project specified, not missing --> ok."""
    from tests.test_utils import mock_nosuchbucket

    # Get project
    project: models.Project = models.Project.query.first()
    assert project

    # Use sto2 -- sto4_start_time not set --------------------------------------------
    assert not project.responsible_unit.sto4_start_time

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["add-missing-bucket", "--project-id", project.public_id]
    )
    assert result.exit_code == 0

    # Verify output
    _, err = capfd.readouterr()
    assert (
        f"Bucket for project '{project.public_id}' found; Bucket not missing. Will not create bucket."
        in err
    )
    assert f"Safespring location for project '{project.public_id}': sto2" in err
    # ---------------------------------------------------------------------------------

    # Use sto2 -- sto4_start_time set, but project created before ---------------------
    # Set start time
    project.responsible_unit.sto4_start_time = current_time()
    db.session.commit()

    # Verify
    assert project.responsible_unit.sto4_start_time
    assert project.date_created < project.responsible_unit.sto4_start_time

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["add-missing-bucket", "--project-id", project.public_id]
    )
    assert result.exit_code == 0

    # Verify output
    _, err = capfd.readouterr()
    assert (
        f"Bucket for project '{project.public_id}' found; Bucket not missing. Will not create bucket."
        in err
    )
    assert f"Safespring location for project '{project.public_id}': sto2" in err
    # ---------------------------------------------------------------------------------

    # Use sto2 -- sto4_start_time set, project created after, but not all vars set ----
    # Set start time
    project.responsible_unit.sto4_start_time = current_time() - relativedelta(hours=1)
    db.session.commit()

    # Verify
    unit = project.responsible_unit
    assert unit.sto4_start_time
    assert project.date_created > unit.sto4_start_time
    assert not all([unit.sto4_endpoint, unit.sto4_name, unit.sto4_access, unit.sto4_secret])

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["add-missing-bucket", "--project-id", project.public_id]
    )
    assert result.exit_code == 1

    # Verify output
    _, err = capfd.readouterr()
    assert (
        f"Bucket for project '{project.public_id}' found; Bucket not missing. Will not create bucket."
        not in err
    )
    assert f"Safespring location for project '{project.public_id}': sto2" not in err
    assert f"Safespring location for project '{project.public_id}': sto4" not in err
    assert f"One or more sto4 variables are missing for unit {unit.public_id}." in err

    # ---------------------------------------------------------------------------------

    # Use sto4 -- sto4_start_time set, project created after and all vars set
    # Set start time
    project.responsible_unit.sto4_endpoint = "endpoint"
    project.responsible_unit.sto4_name = "name"
    project.responsible_unit.sto4_access = "access"
    project.responsible_unit.sto4_secret = "secret"
    db.session.commit()

    # Verify
    unit = project.responsible_unit
    assert unit.sto4_start_time
    assert project.date_created > unit.sto4_start_time
    assert all([unit.sto4_endpoint, unit.sto4_name, unit.sto4_access, unit.sto4_secret])

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["add-missing-bucket", "--project-id", project.public_id]
    )
    assert result.exit_code == 0

    # Verify output
    _, err = capfd.readouterr()
    assert (
        f"Bucket for project '{project.public_id}' found; Bucket not missing. Will not create bucket."
        in err
    )
    assert f"Safespring location for project '{project.public_id}': sto2" not in err
    assert f"Safespring location for project '{project.public_id}': sto4" in err
    assert f"One or more sto4 variables are missing for unit {unit.public_id}." not in err
    # ---------------------------------------------------------------------------------


# lost_files_s3_db -- delete_lost_files


def test_delete_lost_files_no_project(client, cli_runner):
    """flask lost-files delete: no project specified (required)."""
    # Run command
    result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["delete"])

    # Get output from result and verify that help message printed
    assert result.exit_code == 2
    assert "Missing option '--project-id' / '-p'." in result.stdout


def test_delete_lost_files_project_nonexistent(client, cli_runner, capfd: LogCaptureFixture):
    """flask lost-files delete: no such project --> print out error."""
    # Project -- doesn't exist
    project_id: str = "nonexistentproject"
    assert not models.Project.query.filter_by(public_id=project_id).one_or_none()

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["delete", "--project-id", project_id]
    )
    assert result.exit_code == 1

    # Verify output
    _, err = capfd.readouterr()
    assert f"No such project: '{project_id}'" in err


def test_delete_lost_files_deleted(client, cli_runner, boto3_session, capfd: LogCaptureFixture):
    """flask lost-files delete: project specified and exists --> deleted files ok."""
    # Get project
    project: models.Project = models.Project.query.first()
    assert project
    num_project_files = len(project.files)
    assert num_project_files > 0

    # Use sto2 -- sto4_start_time not set -----------------------------------
    assert not project.responsible_unit.sto4_start_time

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["delete", "--project-id", project.public_id]
    )
    assert result.exit_code == 0

    # Verify output - files deleted
    _, err = capfd.readouterr()
    assert f"Files deleted from S3: 0" in err
    assert f"Files deleted from DB: {num_project_files}" in err
    assert f"Safespring location for project '{project.public_id}': sto2" in err
    # ------------------------------------------------------------------------

    # Use sto2 -- start_time set, but project created before -----------------
    # Set start_time
    project.responsible_unit.sto4_start_time = current_time()
    db.session.commit()

    # Verify
    unit = project.responsible_unit
    assert unit.sto4_start_time
    assert project.date_created < unit.sto4_start_time

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["delete", "--project-id", project.public_id]
    )
    assert result.exit_code == 0

    # Verify output - files deleted
    _, err = capfd.readouterr()
    assert f"Files deleted from S3: 0" in err
    assert f"Files deleted from DB: 0" in err  # Already deleted
    assert f"Safespring location for project '{project.public_id}': sto2" in err
    # ------------------------------------------------------------------------

    # Use sto2 -- start_time set, project created after, but all vars not set
    # Set start_time
    project.responsible_unit.sto4_start_time = current_time() - relativedelta(hours=1)
    db.session.commit()

    # Verify
    unit = project.responsible_unit
    assert unit.sto4_start_time
    assert project.date_created > unit.sto4_start_time
    assert not all([unit.sto4_endpoint, unit.sto4_name, unit.sto4_access, unit.sto4_secret])

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["delete", "--project-id", project.public_id]
    )
    assert result.exit_code == 1

    # Verify output - files deleted
    _, err = capfd.readouterr()
    assert f"Files deleted from S3: 0" not in err
    assert f"Files deleted from DB: 0" not in err
    assert f"Safespring location for project '{project.public_id}': sto2" not in err
    assert f"One or more sto4 variables are missing for unit {unit.public_id}." in err
    # ------------------------------------------------------------------------

    # Use sto4 - start_time set, project created after and all vars set ------
    # Set start_time
    project.responsible_unit.sto4_endpoint = "endpoint"
    project.responsible_unit.sto4_name = "name"
    project.responsible_unit.sto4_access = "access"
    project.responsible_unit.sto4_secret = "secret"
    db.session.commit()

    # Verify
    unit = project.responsible_unit
    assert unit.sto4_start_time
    assert project.date_created > unit.sto4_start_time
    assert all([unit.sto4_endpoint, unit.sto4_name, unit.sto4_access, unit.sto4_secret])

    # Run command
    result: click.testing.Result = cli_runner.invoke(
        lost_files_s3_db, ["delete", "--project-id", project.public_id]
    )
    assert result.exit_code == 0

    # Verify output - files deleted
    _, err = capfd.readouterr()
    assert f"Files deleted from S3: 0" in err
    assert f"Files deleted from DB: 0" in err  # Aldready deleted
    assert f"Safespring location for project '{project.public_id}': sto2" not in err
    assert f"Safespring location for project '{project.public_id}': sto4" in err
    assert f"One or more sto4 variables are missing for unit {unit.public_id}." not in err
    # ------------------------------------------------------------------------


def test_delete_lost_files_sqlalchemyerror(
    client, cli_runner, boto3_session, capfd: LogCaptureFixture
):
    """flask lost-files delete: sqlalchemyerror during deletion."""
    # Imports
    from tests.api.test_project import mock_sqlalchemyerror

    # Get project
    project: models.Project = models.Project.query.first()
    assert project
    num_project_files = len(project.files)
    assert num_project_files > 0

    # Mock commit --> no delete
    with patch("dds_web.db.session.commit", mock_sqlalchemyerror):
        # Run command
        result: click.testing.Result = cli_runner.invoke(
            lost_files_s3_db, ["delete", "--project-id", project.public_id]
        )
        assert result.exit_code == 1

    # Verify output - files deleted
    _, err = capfd.readouterr()
    assert "Unable to delete the database entries" in err
    assert f"Files deleted from S3: 0" not in err
    assert f"Files deleted from DB: 0" not in err


# usage = 0 --> check log
def test_monitor_usage_no_usage(client, cli_runner, capfd: LogCaptureFixture):
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
def test_monitor_usage_no_email(client, cli_runner, capfd: LogCaptureFixture):
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
def test_monitor_usage_warning_sent(client, cli_runner, capfd: LogCaptureFixture):
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

        with mail.record_messages() as outbox:
            # Run command
            _: click.testing.Result = cli_runner.invoke(monitor_usage)
            # capture output
            _, err = capfd.readouterr()

            i = 0
            for unit in models.Unit.query.all():
                # Verify email has been sent to the correct recipient
                assert outbox[i].recipients[0] == unit.contact_email
                assert outbox[i].recipients[1] == "delivery@scilifelab.se"
                assert "Your unit is approaching the allocated data quota" in err
                assert f"Unit name: {unit.name}" in err
                i += 1


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


@mock.patch("boto3.session.Session")
def test_set_expired_to_archived_db_failed(
    _: MagicMock, client, cli_runner, capfd: LogCaptureFixture
):
    """Reproduce the error when the s3 bucket is deleted but the DB update fails."""
    # Get the project and set up as expired
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    for status in project.project_statuses:
        status.deadline = current_time() - timedelta(weeks=1)
        status.status = "Expired"

    mock_query = MagicMock()
    mock_query.filter.return_value.delete.side_effect = sqlalchemy.exc.OperationalError(
        "OperationalError", "test", "sqlalchemy"
    )
    with patch("dds_web.database.models.File.query", mock_query):
        with patch("flask.request", False):
            cli_runner.invoke(set_expired_to_archived)

    # Check the logs for the error message
    _, err = capfd.readouterr()
    print(err)
    assert (
        "Project bucket contents were deleted, but they were not deleted from the database. Please contact SciLifeLab Data Centre."
    ) in err
    assert ("SQL: OperationalError") in err


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


# monthly usage


def test_monthly_usage_mark_as_done(client, cli_runner, capfd: LogCaptureFixture):
    """Projects should be marked as done."""
    # Imports
    from tests.api.test_project import mock_sqlalchemyerror

    # Helper function - can be moved out if we need to use in other places later
    def create_file_versions(project: models.Project):
        """Create file versions for project."""
        # Create new file in project
        new_file = models.File(
            name=f"filename_{project.public_id}",
            name_in_bucket=f"name_in_bucket_{project.public_id}",
            subpath=f"filename/subpath",
            size_original=15000,
            size_stored=10000,
            compressed=True,
            salt="A" * 32,
            public_key="B" * 64,
            checksum="C" * 64,
        )
        project.files.append(new_file)

        # Create new versions
        for x in range(3):
            new_version = models.Version(
                size_stored=10000 * x,
                time_uploaded=current_time() - timedelta(days=1),
                time_deleted=current_time(),
            )
            project.file_versions.append(new_version)
            new_file.versions.append(new_version)
            db.session.add(new_file)

        db.session.commit()

    # Check if there's a non active project
    non_active_projects = models.Project.query.filter_by(is_active=False).all()
    project: models.Project = None
    if not non_active_projects:
        # Make at least one project not active
        project = models.Project.query.first()
        project.is_active = False
        db.session.commit()
    else:
        project = non_active_projects[0]

    # There needs to be file versions in non active project
    if not project.file_versions:
        create_file_versions(project=project)
    assert project.file_versions

    # Get active project - to verify that nothing happens with it
    project_active: models.Project = models.Project.query.filter_by(is_active=True).first()

    # There needs to be file versions in active project
    if not project_active.file_versions:
        create_file_versions(project=project_active)
    assert project_active.file_versions

    # Set file versions as invoiced
    for version in project.file_versions:
        time_now = current_time()
        version.time_deleted = time_now
        version.time_invoiced = time_now
    db.session.commit()

    # 1. Marking projects as done
    # Run command - commit should result in sqlalchemy query
    with mail.record_messages() as outbox1:
        with patch("dds_web.db.session.commit", mock_sqlalchemyerror):
            cli_runner.invoke(monthly_usage)

        # Check that non-active project is not marked as done
        assert not project.done
        assert not project_active.done

        # Verify correct logging
        _, logs = capfd.readouterr()
        assert (
            "Usage collection <failed> during step 1: marking projects as done. Sending email..."
            in logs
        )
        assert "Calculating usage..." not in logs

        # Error email should be sent
        assert len(outbox1) == 1
        assert (
            "[INVOICING CRONJOB] (LOCAL_DEVELOPMENT) <ERROR> Error in monthly-usage cronjob"
            == outbox1[-1].subject
        )
        assert "What to do:" in outbox1[-1].body

        # No usage rows should have been saved
        num_usage_rows = models.Usage.query.count()
        assert num_usage_rows == 0

    # 2. Calculating project usage
    # Run command again - part 1 should be successful
    with mail.record_messages() as outbox2:
        with patch("dds_web.db.session.add_all", mock_sqlalchemyerror):
            cli_runner.invoke(monthly_usage)

        # The non-active project should have been marked as done
        assert project.done
        assert not project_active.done

        # Verify correct logging
        _, logs = capfd.readouterr()
        assert (
            "Usage collection <failed> during step 1: marking projects as done. Sending email..."
            not in logs
        )
        assert "Calculating usage..." in logs
        assert f"Project {project.public_id} byte hours:" not in logs
        assert f"Project {project_active.public_id} byte hours:" in logs
        assert (
            "Usage collection <failed> during step 2: calculating and saving usage. Sending email..."
            in logs
        )

        # Error email should have been sent
        assert len(outbox2) == 1
        assert (
            "[INVOICING CRONJOB] (LOCAL_DEVELOPMENT) <ERROR> Error in monthly-usage cronjob"
            == outbox2[-1].subject
        )
        assert "What to do:" in outbox2[-1].body

        # Project versions should not be altered
        assert project_active.file_versions
        for version in project_active.file_versions:
            assert version.time_deleted != version.time_invoiced

        # No usage rows should've been saved
        usage_row_1 = models.Usage.query.filter_by(project_id=project.id).one_or_none()
        usage_row_2 = models.Usage.query.filter_by(project_id=project_active.id).one_or_none()
        assert not usage_row_1
        assert not usage_row_2

    # 3. Send success email
    # Run command a third time - part 1 and 2 should be successful
    with mail.record_messages() as outbox3:
        cli_runner.invoke(monthly_usage)

        # Verify correct logging
        _, logs = capfd.readouterr()
        assert (
            "Usage collection <failed> during step 1: marking projects as done. Sending email..."
            not in logs
        )
        assert (
            "Usage collection <failed> during step 2: calculating and saving usage. Sending email..."
            not in logs
        )
        assert "Usage collection successful; Sending email." in logs

        # Email should be sent
        assert len(outbox3) == 1
        assert (
            "[INVOICING CRONJOB] (LOCAL_DEVELOPMENT) Usage records available for collection"
            == outbox3[-1].subject
        )
        assert (
            "The calculation of the monthly usage succeeded; The byte hours for all active projects have been saved to the database."
            in outbox3[-1].body
        )

        # Project versions should have been altered
        for version in project_active.file_versions:
            assert version.time_deleted == version.time_invoiced

        # Usage rows should have been saved for active project
        usage_row_1 = models.Usage.query.filter_by(project_id=project.id).one_or_none()
        usage_row_2 = models.Usage.query.filter_by(project_id=project_active.id).one_or_none()
        assert not usage_row_1
        assert usage_row_2


def test_monthly_usage_no_instance_name(client, cli_runner, capfd: LogCaptureFixture):
    """Test that the command do not send an email with the name if it is not set."""

    import flask

    assert flask.current_app.config.get("INSTANCE_NAME") == "LOCAL_DEVELOPMENT"
    # Set the instance name to none
    flask.current_app.config["INSTANCE_NAME"] = None

    with mail.record_messages() as outbox:
        cli_runner.invoke(monthly_usage)

        # Email should be sent
        assert len(outbox) == 1
        assert "[INVOICING CRONJOB] Usage records available for collection" == outbox[-1].subject
        assert (
            "The calculation of the monthly usage succeeded; The byte hours for all active projects have been saved to the database."
            == outbox[-1].body
        )


def test_collect_stats(client, cli_runner, fs: FakeFilesystem):
    """Test that the reporting is giving correct values."""
    from dds_web.database.models import (
        Unit,
        UnitUser,
        ResearchUser,
        SuperAdmin,
        User,
        Reporting,
        Project,
        ProjectUsers,
        Version,
    )
    from dds_web.utils import bytehours_in_last_month, page_query, calculate_bytehours
    import dds_web.utils

    def verify_reporting_row(row, time_date):
        """Verify correct values in reporting row."""
        assert row.date.date() == datetime.date(time_date)
        assert row.unit_count == Unit.query.count()
        assert row.researcher_count == ResearchUser.query.count()
        assert row.unit_personnel_count == UnitUser.query.filter_by(is_admin=False).count()
        assert row.unit_admin_count == UnitUser.query.filter_by(is_admin=True).count()
        assert row.superadmin_count == SuperAdmin.query.count()
        assert row.total_user_count == User.query.count()
        assert row.total_user_count == sum(
            [
                row.researcher_count,
                row.unit_personnel_count,
                row.unit_admin_count,
                row.superadmin_count,
            ]
        )
        assert row.project_owner_unique_count == (
            ProjectUsers.query.filter_by(owner=True)
            .with_entities(ProjectUsers.user_id)
            .distinct()
            .count()
        )
        assert row.total_project_count == Project.query.count()
        assert row.active_project_count == Project.query.filter_by(is_active=True).count()
        assert row.inactive_project_count == Project.query.filter_by(is_active=False).count()
        assert row.total_project_count == sum(
            [
                row.active_project_count,
                row.inactive_project_count,
            ]
        )
        assert row.tb_stored_now == round(
            sum(proj.size for proj in Project.query) / 1000000000000, 2
        )
        assert row.tb_uploaded_since_start == round(
            sum(version.size_stored for version in dds_web.utils.page_query(Version.query))
            / 1000000000000,
            2,
        )
        assert row.tbhours == round(
            sum(bytehours_in_last_month(version=version) for version in page_query(Version.query))
            / 1e12,
            2,
        )
        assert row.tbhours_since_start == round(
            sum(
                calculate_bytehours(
                    minuend=version.time_deleted or time_date,
                    subtrahend=version.time_uploaded,
                    size_bytes=version.size_stored,
                )
                for version in page_query(Version.query)
            )
            / 1e12,
            2,
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


def test_send_usage(client, cli_runner, capfd: LogCaptureFixture):
    """Test that the email with the usage report is send"""
    # Imports
    from dds_web.database.models import Usage

    # Get projects
    projects = models.Project.query.filter(
        models.Project.public_id.in_(
            ["public_project_id", "second_public_project_id", "unit2testing"]
        )
    ).all()
    project_1_unit_1 = next(p for p in projects if p.public_id == "public_project_id")
    project_2_unit_1 = next(p for p in projects if p.public_id == "second_public_project_id")
    project_1_unit_2 = next(p for p in projects if p.public_id == "unit2testing")

    # Loop to populate usage table with fake entries across two years
    january_2021 = datetime(2021, 1, 1)  # Start at Jan 2021
    usage_list = []
    for i in range(25):
        time = january_2021 + relativedelta(months=i)
        usage_1 = Usage(
            project_id=project_1_unit_1.id,
            usage=100,
            time_collected=time,
        )
        usage_2 = Usage(
            project_id=project_2_unit_1.id,
            usage=100,
            time_collected=time,
        )
        usage_3 = Usage(
            project_id=project_1_unit_2.id,
            usage=100,
            time_collected=time,
        )
        usage_list.extend([usage_1, usage_2, usage_3])

    db.session.add_all(usage_list)
    db.session.commit()
    # Fake data included from Jan 2021 to Jan 2023

    def run_command_and_check_output(months_to_test, start_time):
        """
        This function tests the output of the `send_usage` command by running the command with given arguments and checking the output.
        It mocks the current time and checks that the email sent contains the correct subject and body.
        It also checks that the csv files attached to the email have the correct names and content.

        Return the csv files attached to the email.
        """

        csv_file_location = "/tmp/"

        with mail.record_messages() as outbox:
            with patch("dds_web.utils.current_time") as current_time_func:  # Mock current time
                current_time_func.return_value = start_time
                cli_runner.invoke(send_usage, ["--months", months_to_test])

            # Verify output and sent email
            assert len(outbox) == 1
            assert (
                "[SEND-USAGE CRONJOB] (LOCAL_DEVELOPMENT) Usage records attached in the present mail"
                in outbox[-1].subject
            )
            assert f"Here is the usage for the last {months_to_test} months." in outbox[-1].body

            end_time = start_time - relativedelta(months=months_to_test)
            start_month = start_time.month
            end_month = end_time.month
            unit_1_id = project_1_unit_1.responsible_unit.public_id
            unit_2_id = project_1_unit_2.responsible_unit.public_id
            csv_1_name = (
                f"{csv_file_location}{unit_1_id}_Usage_Months-{end_month}-to-{start_month}.csv"
            )
            csv_2_name = (
                f"{csv_file_location}{unit_2_id}_Usage_Months-{end_month}-to-{start_month}.csv"
            )

            # check that the files no longer exist in the filesystem
            assert not os.path.exists(csv_1_name)
            assert not os.path.exists(csv_2_name)

            _, logs = capfd.readouterr()
            assert f"Month now: {start_month}" in logs
            assert f"Month {months_to_test} months ago: {end_month}" in logs
            assert f"CSV file name: {csv_1_name}" in logs
            assert f"CSV file name: {csv_2_name}" in logs
            assert "Sending email with the CSV." in logs

            # Verify that the csv files are attached - two files, one for each unit
            assert len(outbox[-1].attachments) == 2
            for attachment, file_name in zip(outbox[-1].attachments, [csv_1_name, csv_2_name]):
                assert attachment.filename == file_name
                assert attachment.content_type == "text/csv"

            # Check csv content
            # retrieve the files from the email
            csv_1 = outbox[-1].attachments[0].data
            csv_2 = outbox[-1].attachments[1].data

            # check that the header and summatory at the end is correct
            assert "Project ID,Project Title,Project Created,Time Collected,Byte Hours" in csv_1
            assert "Project ID,Project Title,Project Created,Time Collected,Byte Hours" in csv_2
            usage = 100.0 * months_to_test * 2  # 2 projects
            assert f"--,--,--,--,{str(usage)}" in csv_1
            usage = 100.0 * months_to_test
            assert f"--,--,--,--,{str(usage)}" in csv_2

            # check that the content is correct
            import re

            csv_1 = re.split(",|\n", csv_1)  # split by comma or newline
            csv_2 = re.split(",|\n", csv_2)

            # Projects and data is correct
            assert csv_1.count("public_project_id") == months_to_test
            assert csv_1.count("second_public_project_id") == months_to_test
            assert csv_1.count("unit2testing") == 0  # this project is not in the unit
            assert csv_1.count("100.0") == months_to_test * 2

            assert csv_2.count("public_project_id") == 0  # this project is not in the unit
            assert csv_2.count("second_public_project_id") == 0  # this project is not in the unit
            assert csv_2.count("unit2testing") == months_to_test
            assert csv_2.count("100.0") == months_to_test

            # Check that the months included in the report are the correct ones
            # move start time to the first day of the month
            start_collected_time = start_time.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            for i in range(months_to_test):
                check_time_collected = start_collected_time - relativedelta(
                    months=i
                )  # every month is included
                assert f"{check_time_collected}" in csv_1
                assert f"{check_time_collected}" in csv_1
        return csv_1, csv_2

    # Test that the command works for 4 months from Jan 2022
    start_time = datetime(2022, 1, 15)  # Mid Jan 2022
    csv_1, csv_2 = run_command_and_check_output(months_to_test=4, start_time=start_time)
    # Hardcode the expected csv content to double check
    # October, November, December, January (4 months)
    assert "2021-10-01 00:00:00" in csv_1
    assert "2021-11-01 00:00:00" in csv_1
    assert "2021-12-01 00:00:00" in csv_1
    assert "2022-01-01 00:00:00" in csv_1
    assert "2021-10-01 00:00:00" in csv_2
    assert "2021-11-01 00:00:00" in csv_2
    assert "2021-12-01 00:00:00" in csv_2
    assert "2022-01-01 00:00:00" in csv_2

    # Test that the command works for 4 months from May 2022
    start_time = datetime(2022, 5, 15)  # Mid May 2022
    csv_1, csv_2 = run_command_and_check_output(months_to_test=4, start_time=start_time)
    # Hardcode the expected csv content to double check
    # February, March, April, May (4 months)
    assert "2022-02-01 00:00:00" in csv_1
    assert "2022-03-01 00:00:00" in csv_1
    assert "2022-04-01 00:00:00" in csv_1
    assert "2022-05-01 00:00:00" in csv_1
    assert "2022-02-01 00:00:00" in csv_2
    assert "2022-03-01 00:00:00" in csv_2
    assert "2022-04-01 00:00:00" in csv_2
    assert "2022-05-01 00:00:00" in csv_2

    # Test that the command works for 4 months from Sept 2022
    start_time = datetime(2022, 9, 15)  # Mid Sep 2022
    csv_1, csv_2 = run_command_and_check_output(months_to_test=4, start_time=start_time)
    # Hardcode the expected csv content to double check
    # June, July, August, September (4 months)
    assert "2022-06-01 00:00:00" in csv_1
    assert "2022-07-01 00:00:00" in csv_1
    assert "2022-08-01 00:00:00" in csv_1
    assert "2022-09-01 00:00:00" in csv_1
    assert "2022-06-01 00:00:00" in csv_2
    assert "2022-07-01 00:00:00" in csv_2
    assert "2022-08-01 00:00:00" in csv_2
    assert "2022-09-01 00:00:00" in csv_2


def test_send_usage_error_csv(client, cli_runner, capfd: LogCaptureFixture):
    """Test that checks errors in the csv handling"""

    with mail.record_messages() as outbox:
        with patch("csv.writer") as mock_writing_file:
            mock_writing_file.side_effect = IOError()
            cli_runner.invoke(send_usage, ["--months", 3])

        _, logs = capfd.readouterr()
        assert "Error writing to CSV file:" in logs  # error in writing the csv file
        assert "No CSV files generated." in logs  # no csv files generated

        # Check that no files were generated in the fs
        assert not os.path.exists("*.csv")

        # Verify error email :- At least one email was sent
        assert len(outbox) == 1
        assert (
            "[SEND-USAGE CRONJOB] (LOCAL_DEVELOPMENT) <ERROR> Error in send-usage cronjob"
            == outbox[-1].subject
        )
        assert "There was an error in the cronjob 'send-usage'" in outbox[-1].body


## run-worker
def test_restart_redis__worker(client, cli_runner, mock_queue_redis):
    """Test that starts the redis workers"""

    with patch("dds_web.commands.Worker") as mock_worker:
        with patch("dds_web.commands.Worker.all") as mock_get_all:
            with patch("dds_web.commands.send_shutdown_command") as mock_send_shutdown_command:

                mock_worker_instance = MagicMock()
                mock_worker.return_value = mock_worker_instance
                mock_send_shutdown_command.return_value = MagicMock()

                mock_get_all.return_value = [MagicMock(name="worker1"), MagicMock(name="worker2")]

                cli_runner.invoke(restart_redis_worker)

                mock_worker_instance.work.assert_called_once()  # work method called
