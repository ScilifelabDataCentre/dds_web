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
from dateutil.relativedelta import relativedelta

# Installed
import click
from pyfakefs.fake_filesystem import FakeFilesystem
import flask_mail
import freezegun
import rich.prompt

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
    lost_files_s3_db,
    update_unit,
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


# # fill_db_wrapper


# def test_fill_db_wrapper_production(client, runner, capfd) -> None:
#     """Run init-db with the production argument."""
#     result: click.testing.Result = runner.invoke(fill_db_wrapper, ["production"])
#     _, err = capfd.readouterr()
#     assert "already exists, not creating user" in err


# def test_fill_db_wrapper_devsmall(client, runner, capfd) -> None:
#     """Run init-db with the dev-small argument."""
#     result: click.testing.Result = runner.invoke(fill_db_wrapper, ["dev-small"])
#     _, err = capfd.readouterr()
#     assert "Initializing development db" in err
#     assert "DB filled" not in err  # DB already filled, duplicates.


# # def test_fill_db_wrapper_devbig(client, runner) -> None:
# #     """Run init-db with the dev-big argument."""
# #     result: click.testing.Result = runner.invoke(fill_db_wrapper, ["dev-big"])
# #     assert result.exit_code == 1

# # create_new_unit


# def create_command_options_from_dict(options: typing.Dict) -> typing.List:
#     """Create a list with options and values from a dict."""
#     # Create command options
#     command_options: typing.List = []
#     for key, val in options.items():
#         command_options.append(f"--{key}")
#         command_options.append(val)

#     return command_options


# correct_unit: typing.Dict = {
#     "name": "newname",
#     "public_id": "newpublicid",
#     "external_display_name": "newexternaldisplay",
#     "contact_email": "newcontact@mail.com",
#     "internal_ref": "newinternalref",
#     "sto2_endpoint": "newsafespringendpoint",
#     "sto2_name": "newsafespringname",
#     "sto2_access": "newsafespringaccess",
#     "sto2_secret": "newsafespringsecret",
#     "days_in_available": 45,
#     "days_in_expired": 15,
# }


# def test_create_new_unit_public_id_too_long(client, runner) -> None:
#     """Create new unit, public_id too long."""
#     # Change public_id
#     incorrect_unit: typing.Dict = correct_unit.copy()
#     incorrect_unit["public_id"] = "public" * 10

#     # Get command options
#     command_options = create_command_options_from_dict(options=incorrect_unit)

#     # Run command
#     result: click.testing.Result = runner.invoke(create_new_unit, command_options)
#     # assert "The 'public_id' can be a maximum of 50 characters" in result.output
#     assert (
#         not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
#     )


# def test_create_new_unit_public_id_incorrect_characters(client, runner) -> None:
#     """Create new unit, public_id has invalid characters (here _)."""
#     # Change public_id
#     incorrect_unit: typing.Dict = correct_unit.copy()
#     incorrect_unit["public_id"] = "new_public_id"

#     # Get command options
#     command_options = create_command_options_from_dict(options=incorrect_unit)

#     # Run command
#     result: click.testing.Result = runner.invoke(create_new_unit, command_options)
#     # assert "The 'public_id' can only contain letters, numbers, dots (.) and hyphens (-)." in result.output
#     assert (
#         not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
#     )


# def test_create_new_unit_public_id_starts_with_dot(client, runner) -> None:
#     """Create new unit, public_id starts with invalid character (. or -)."""
#     # Change public_id
#     incorrect_unit: typing.Dict = correct_unit.copy()
#     incorrect_unit["public_id"] = ".newpublicid"

#     # Get command options
#     command_options = create_command_options_from_dict(options=incorrect_unit)

#     # Run command
#     result: click.testing.Result = runner.invoke(create_new_unit, command_options)
#     # assert "The 'public_id' must begin with a letter or number." in result.output
#     assert (
#         not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
#     )

#     # Change public_id again
#     incorrect_unit["public_id"] = "-newpublicid"

#     # Get command options
#     command_options = create_command_options_from_dict(options=incorrect_unit)

#     # Run command
#     result: click.testing.Result = runner.invoke(create_new_unit, command_options)
#     # assert "The 'public_id' must begin with a letter or number." in result.output
#     assert (
#         not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
#     )


# def test_create_new_unit_public_id_too_many_dots(client, runner) -> None:
#     """Create new unit, public_id has invalid number of dots."""
#     # Change public_id
#     incorrect_unit: typing.Dict = correct_unit.copy()
#     incorrect_unit["public_id"] = "new.public..id"

#     # Get command options
#     command_options = create_command_options_from_dict(options=incorrect_unit)

#     # Run command
#     result: click.testing.Result = runner.invoke(create_new_unit, command_options)
#     # assert "The 'public_id' should not contain more than two dots." in result.output
#     assert (
#         not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
#     )


# def test_create_new_unit_public_id_invalid_start(client, runner) -> None:
#     """Create new unit, public_id starts with prefix."""
#     # Change public_id
#     incorrect_unit: typing.Dict = correct_unit.copy()
#     incorrect_unit["public_id"] = "xn--newpublicid"

#     # Get command options
#     command_options = create_command_options_from_dict(options=incorrect_unit)

#     # Run command
#     result: click.testing.Result = runner.invoke(create_new_unit, command_options)
#     # assert "The 'public_id' cannot begin with the 'xn--' prefix." in result.output
#     assert (
#         not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
#     )


# def test_create_new_unit_success(client, runner) -> None:
#     """Create new unit, public_id starts with prefix."""
#     # Get command options
#     command_options = create_command_options_from_dict(options=correct_unit)

#     with patch("dds_web.db.session.commit", mock_commit):
#         # Run command
#         result: click.testing.Result = runner.invoke(create_new_unit, command_options)
#         # assert f"Unit '{correct_unit['name']}' created" in result.output


# # update_unit


# def test_update_unit_no_such_unit(client, runner, capfd) -> None:
#     """Try to update a non existent unit -> Error."""
#     # Create command options
#     command_options: typing.List = [
#         "--unit-id",
#         "unitdoesntexist",
#         "--sto4-endpoint",
#         "endpoint_sto4",
#         "--sto4-name",
#         "name_sto4",
#         "--sto4-access",
#         "access_sto4",
#         "--sto4-secret",
#         "secret_sto4",
#     ]

#     # Run command
#     result: click.testing.Result = runner.invoke(update_unit, command_options)
#     assert result.exit_code == 0
#     assert not result.output

#     # Get logging
#     _, err = capfd.readouterr()

#     # Verify message
#     assert f"There is no unit with the public ID '{command_options[1]}'." in err


# def test_update_unit_sto4_start_time_exists_mock_prompt_False(client, runner, capfd) -> None:
#     """Start time already recorded. Answer no to prompt about update anyway. No changes should be made."""
#     # Get existing unit
#     unit: models.Unit = models.Unit.query.first()
#     unit_id: str = unit.public_id

#     # Get sto4 info from start
#     sto4_endpoint_original = unit.sto4_endpoint
#     sto4_name_original = unit.sto4_name
#     sto4_access_original = unit.sto4_access
#     sto4_secret_original = unit.sto4_secret
#     sto4_info_original = [
#         sto4_endpoint_original,
#         sto4_name_original,
#         sto4_access_original,
#         sto4_secret_original,
#     ]
#     assert sto4_info_original == [None, None, None, None]

#     # Set sto4 start time
#     unit.sto4_start_time = current_time()
#     db.session.commit()

#     # Create command options
#     command_options: typing.List = [
#         "--unit-id",
#         unit_id,
#         "--sto4-endpoint",
#         "endpoint_sto4",
#         "--sto4-name",
#         "name_sto4",
#         "--sto4-access",
#         "access_sto4",
#         "--sto4-secret",
#         "secret_sto4",
#     ]

#     # Run command
#     # Mock rich prompt - False
#     with patch.object(rich.prompt.Confirm, "ask", return_value=False) as mock_ask:
#         result: click.testing.Result = runner.invoke(update_unit, command_options)
#         assert result.exit_code == 0
#         assert not result.output
#     mock_ask.assert_called_once

#     # Get logging
#     _, err = capfd.readouterr()

#     # Verify logging
#     assert f"Cancelling sto4 update for unit '{unit_id}'." in err
#     assert f"Unit '{unit_id}' updated successfully" not in err

#     # Verify no change in unit
#     unit: models.Unit = models.Unit.query.filter_by(public_id=unit_id).first()
#     assert unit
#     assert [
#         unit.sto4_endpoint,
#         unit.sto4_name,
#         unit.sto4_access,
#         unit.sto4_secret,
#     ] == sto4_info_original


# def test_update_unit_sto4_start_time_exists_mock_prompt_True(client, runner, capfd) -> None:
#     """Start time already recorded. Answer yes to prompt about update anyway. Changes should be made."""
#     # Get existing unit
#     unit: models.Unit = models.Unit.query.first()
#     unit_id: str = unit.public_id

#     # Get sto4 info from start
#     sto4_endpoint_original = unit.sto4_endpoint
#     sto4_name_original = unit.sto4_name
#     sto4_access_original = unit.sto4_access
#     sto4_secret_original = unit.sto4_secret
#     sto4_info_original = [
#         sto4_endpoint_original,
#         sto4_name_original,
#         sto4_access_original,
#         sto4_secret_original,
#     ]
#     assert sto4_info_original == [None, None, None, None]

#     # Set sto4 start time
#     unit.sto4_start_time = current_time()
#     db.session.commit()

#     # Create command options
#     command_options: typing.List = [
#         "--unit-id",
#         unit_id,
#         "--sto4-endpoint",
#         "endpoint_sto4",
#         "--sto4-name",
#         "name_sto4",
#         "--sto4-access",
#         "access_sto4",
#         "--sto4-secret",
#         "secret_sto4",
#     ]

#     # Run command
#     # Mock rich prompt - True
#     with patch.object(rich.prompt.Confirm, "ask", return_value=True) as mock_ask:
#         result: click.testing.Result = runner.invoke(update_unit, command_options)
#         assert result.exit_code == 0
#         assert not result.output
#     mock_ask.assert_called_once

#     # Get logging
#     _, err = capfd.readouterr()

#     # Verify logging
#     assert f"Cancelling sto4 update for unit '{unit_id}'." not in err
#     assert f"Unit '{unit_id}' updated successfully" in err

#     # Verify change in unit
#     unit: models.Unit = models.Unit.query.filter_by(public_id=unit_id).first()
#     assert unit
#     assert [
#         unit.sto4_endpoint,
#         unit.sto4_name,
#         unit.sto4_access,
#         unit.sto4_secret,
#     ] != sto4_info_original
#     assert [unit.sto4_endpoint, unit.sto4_name, unit.sto4_access, unit.sto4_secret] == [
#         command_options[3],
#         command_options[5],
#         command_options[7],
#         command_options[9],
#     ]


# # update_uploaded_file_with_log


# def test_update_uploaded_file_with_log_nonexisting_project(client, runner, capfd) -> None:
#     """Add file info to non existing project."""
#     # Create command options
#     command_options: typing.List = [
#         "--project",
#         "projectdoesntexist",
#         "--path-to-log-file",
#         "somefile",
#     ]

#     # Run command
#     assert db.session.query(models.Project).all()
#     with patch("dds_web.database.models.Project.query.filter_by", mock_no_project):
#         result: click.testing.Result = runner.invoke(update_uploaded_file_with_log, command_options)
#     _, err = capfd.readouterr()
#     assert "The project 'projectdoesntexist' doesn't exist." in err


# def test_update_uploaded_file_with_log_nonexisting_file(client, runner, fs: FakeFilesystem) -> None:
#     """Attempt to read file which does not exist."""
#     # Verify that fake file does not exist
#     non_existent_log_file: str = "this_is_not_a_file.json"
#     assert not os.path.exists(non_existent_log_file)

#     # Create command options
#     command_options: typing.List = [
#         "--project",
#         "projectdoesntexist",
#         "--path-to-log-file",
#         non_existent_log_file,
#     ]

#     # Run command
#     result: click.testing.Result = runner.invoke(update_uploaded_file_with_log, command_options)
#     # TODO: Add check for logging or change command to return or raise error. capfd does not work together with fs
#     # _, err = capfd.readouterr()
#     # assert "The project 'projectdoesntexist' doesn't exist." in result.stderr


# # lost_files_s3_db


# def test_lost_files_s3_db_no_command(client, cli_runner, capfd):
#     """Test running the flask lost-files command without any subcommand."""
#     _: click.testing.Result = cli_runner.invoke(lost_files_s3_db)
#     _, err = capfd.readouterr()
#     assert not err


# # lost_files_s3_db -- list_lost_files


# def test_list_lost_files_no_such_project(client, cli_runner, capfd):
#     """flask lost-files ls: project specified, project doesnt exist."""
#     # Project ID -- doesn't exist
#     project_id: str = "nonexistentproject"
#     assert not models.Project.query.filter_by(public_id=project_id).one_or_none()

#     # Run command with non existent project
#     result: click.testing.Result = cli_runner.invoke(
#         lost_files_s3_db, ["ls", "--project-id", project_id]
#     )
#     assert result.exit_code == 1  # sys.exit(1)

#     # Verify output
#     _, err = capfd.readouterr()
#     assert f"Searching for lost files in project '{project_id}'." in err
#     assert f"No such project: '{project_id}'" in err


# def test_list_lost_files_no_lost_files_in_project(client, cli_runner, boto3_session, capfd):
#     """flask lost-files ls: project specified, no lost files."""
#     # Get project
#     project = models.Project.query.first()
#     public_id = project.public_id
#     assert project

#     # Use sto2 -- no sto4_endpoint_added date ---------------------------------------------
#     project_unit = project.responsible_unit
#     assert not project_unit.sto4_start_time

#     # Mock project.files -- no files
#     with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
#         mock_files.return_value = []

#         # Run command
#         result: click.testing.Result = cli_runner.invoke(
#             lost_files_s3_db, ["ls", "--project-id", public_id]
#         )
#         assert result.exit_code == 0

#     # Verify output -- no lost files
#     _, err = capfd.readouterr()
#     assert f"Safespring location for project '{public_id}': sto2" in err
#     assert f"Searching for lost files in project '{public_id}'." in err
#     assert f"No lost files in project '{public_id}'" in err
#     # ---------------------------------------------------------------------------------------

#     # Use sto2 -- sto4_endpoint_added but project created before ----------------------------
#     project_unit.sto4_start_time = current_time()
#     db.session.commit()

#     assert project_unit.sto4_start_time
#     assert project.date_created < project_unit.sto4_start_time

#     # Mock project.files -- no files
#     with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
#         mock_files.return_value = []

#         # Run command
#         result: click.testing.Result = cli_runner.invoke(
#             lost_files_s3_db, ["ls", "--project-id", project.public_id]
#         )
#         assert result.exit_code == 0

#     # Verify output -- no lost files
#     _, err = capfd.readouterr()
#     assert f"Safespring location for project '{project.public_id}': sto2" in err
#     assert f"Searching for lost files in project '{project.public_id}'." in err
#     assert f"No lost files in project '{project.public_id}'" in err
#     # ---------------------------------------------------------------------------------------

#     # Use sto2 -- sto4_endpoint_added, project created after, but not all info is available --
#     project_unit.sto4_start_time = current_time() - relativedelta(hours=1)
#     db.session.commit()

#     assert project_unit.sto4_start_time
#     assert project.date_created > project_unit.sto4_start_time
#     assert not all(
#         [
#             project_unit.sto4_endpoint,
#             project_unit.sto4_name,
#             project_unit.sto4_access,
#             project_unit.sto4_secret,
#         ]
#     )

#     # Mock project.files -- no files
#     with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
#         mock_files.return_value = []

#         # Run command
#         result: click.testing.Result = cli_runner.invoke(
#             lost_files_s3_db, ["ls", "--project-id", project.public_id]
#         )
#         assert result.exit_code == 1

#     # Verify output -- no lost files
#     _, err = capfd.readouterr()
#     assert f"One or more sto4 variables are missing for unit {project_unit.public_id}." in err
#     assert f"Safespring location for project '{project.public_id}': sto2" not in err
#     assert f"Searching for lost files in project '{project.public_id}'." in err
#     assert f"No lost files in project '{project.public_id}'" not in err
#     # ---------------------------------------------------------------------------------------

#     # Use sto4 -- sto4_endpoint_added, project created after, and all info is available -----
#     project_unit.sto4_start_time = current_time() - relativedelta(hours=1)
#     project_unit.sto4_endpoint = "endpoint"
#     project_unit.sto4_name = "name"
#     project_unit.sto4_access = "access"
#     project_unit.sto4_secret = "secret"
#     db.session.commit()

#     assert project_unit.sto4_start_time
#     assert project.date_created > project_unit.sto4_start_time
#     assert all(
#         [
#             project_unit.sto4_endpoint,
#             project_unit.sto4_name,
#             project_unit.sto4_access,
#             project_unit.sto4_secret,
#         ]
#     )

#     # Mock project.files -- no files
#     with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
#         mock_files.return_value = []

#         # Run command
#         result: click.testing.Result = cli_runner.invoke(
#             lost_files_s3_db, ["ls", "--project-id", project.public_id]
#         )
#         assert result.exit_code == 0

#     # Verify output -- no lost files
#     _, err = capfd.readouterr()
#     assert f"Safespring location for project '{project.public_id}': sto2" not in err
#     assert f"Safespring location for project '{project.public_id}': sto4" in err
#     assert f"Searching for lost files in project '{project.public_id}'." in err
#     assert f"No lost files in project '{project.public_id}'" in err

#     # ---------------------------------------------------------------------------------------


# def test_list_lost_files_missing_in_s3_in_project(client, cli_runner, boto3_session, capfd):
#     """flask lost-files ls: project specified, lost files in s3."""
#     # Get project
#     project = models.Project.query.first()
#     assert project

#     # Run command
#     result: click.testing.Result = cli_runner.invoke(
#         lost_files_s3_db, ["ls", "--project-id", project.public_id]
#     )
#     assert result.exit_code == 0

#     # Verify output
#     _, err = capfd.readouterr()
#     # All files should be in db but not in s3
#     for f in project.files:
#         assert (
#             f"Entry {f.name_in_bucket} ({project.public_id}, {project.responsible_unit}) not found in S3 (but found in db)"
#             in err
#         )
#         assert (
#             f"Entry {f.name_in_bucket} ({project.public_id}, {project.responsible_unit}) not found in database (but found in s3)"
#             not in err
#         )

#     assert f"Lost files in project: {project.public_id}\t\tIn DB but not S3: {len(project.files)}\tIn S3 but not DB: 0\n"


# def test_list_lost_files_no_lost_files_total(client, cli_runner, boto3_session, capfd):
#     """flask lost-files ls: no project specified, no lost files."""
#     # Use sto2 -- no sto4_endpoint_added date ---------------------------------------------
#     for u in models.Unit.query.all():
#         assert not u.sto4_start_time

#     # Mock project.files -- no files
#     with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
#         mock_files.return_value = []

#         # Run command
#         result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
#         assert result.exit_code == 0

#     # Verify output -- no lost files
#     _, err = capfd.readouterr()
#     assert "Searching for lost files in project" not in err
#     assert "No project specified, searching for lost files in all units." in err
#     for u in models.Unit.query.all():
#         assert f"Listing lost files in unit: {u.public_id}" in err
#         for p in u.projects:
#             assert f"Safespring location for project '{p.public_id}': sto2" in err
#             assert f"Safespring location for project '{p.public_id}': sto4" not in err
#     assert f"No lost files for unit '{u.public_id}'" in err
#     # ---------------------------------------------------------------------------------------

#     # Use sto2 -- sto4_endpoint_added but project created before ----------------------------
#     for u in models.Unit.query.all():
#         u.sto4_start_time = current_time()
#         for p in u.projects:
#             assert p.date_created < u.sto4_start_time
#     db.session.commit()

#     # Mock project.files -- no files
#     with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
#         mock_files.return_value = []

#         # Run command
#         result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
#         assert result.exit_code == 0

#     # Verify output -- no lost files
#     _, err = capfd.readouterr()
#     assert "Searching for lost files in project" not in err
#     assert "No project specified, searching for lost files in all units." in err
#     for u in models.Unit.query.all():
#         assert f"Listing lost files in unit: {u.public_id}" in err
#         for p in u.projects:
#             assert f"Safespring location for project '{p.public_id}': sto2" in err
#             assert f"Safespring location for project '{p.public_id}': sto4" not in err
#     assert f"No lost files for unit '{u.public_id}'" in err
#     # ---------------------------------------------------------------------------------------

#     # Use sto2 -- sto4_endpoint_added, project created after, but not all info is available --
#     for u in models.Unit.query.all():
#         u.sto4_start_time = current_time() - relativedelta(hours=1)
#         for p in u.projects:
#             assert p.date_created > u.sto4_start_time
#     db.session.commit()

#     # Mock project.files -- no files
#     with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
#         mock_files.return_value = []

#         # Run command
#         result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
#         assert result.exit_code == 0

#     # Verify output -- no lost files
#     _, err = capfd.readouterr()
#     assert "Searching for lost files in project" not in err
#     assert "No project specified, searching for lost files in all units." in err
#     for u in models.Unit.query.all():
#         assert f"Listing lost files in unit: {u.public_id}" in err
#         for p in u.projects:
#             assert f"Safespring location for project '{p.public_id}': sto2" not in err
#             assert f"Safespring location for project '{p.public_id}': sto4" not in err
#     assert f"No lost files for unit '{u.public_id}'" in err
#     # ---------------------------------------------------------------------------------------

#     # Use sto4 -- sto4_endpoint_added, project created after, and all info is available -----
#     for u in models.Unit.query.all():
#         u.sto4_start_time = current_time() - relativedelta(hours=1)
#         for p in u.projects:
#             assert p.date_created > u.sto4_start_time
#             u.sto4_endpoint = "endpoint"
#             u.sto4_name = "name"
#             u.sto4_access = "access"
#             u.sto4_secret = "secret"

#     db.session.commit()

#     # Mock project.files -- no files
#     with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
#         mock_files.return_value = []

#         # Run command
#         result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
#         assert result.exit_code == 0

#     # Verify output -- no lost files
#     _, err = capfd.readouterr()
#     assert "Searching for lost files in project" not in err
#     assert "No project specified, searching for lost files in all units." in err
#     for u in models.Unit.query.all():
#         assert f"Listing lost files in unit: {u.public_id}" in err
#         for p in u.projects:
#             assert f"Safespring location for project '{p.public_id}': sto2" not in err
#             assert f"Safespring location for project '{p.public_id}': sto4" in err
#     assert f"No lost files for unit '{u.public_id}'" in err
#     # ---------------------------------------------------------------------------------------

#     # Use sto4 for all but one --------------------------------------------------------------
#     for u in models.Unit.query.all():
#         u.sto4_start_time = current_time() - relativedelta(hours=1)
#         for p in u.projects:
#             assert p.date_created > u.sto4_start_time
#             u.sto4_endpoint = "endpoint"
#             u.sto4_name = "name"
#             u.sto4_access = "access"
#             u.sto4_secret = "secret"

#     unit_no_sto4_endpoint = models.Unit.query.first()
#     unit_no_sto4_endpoint_id = unit_no_sto4_endpoint.public_id
#     unit_no_sto4_endpoint.sto4_endpoint = None
#     db.session.commit()

#     # Mock project.files -- no files
#     with patch("dds_web.database.models.Project.files", new_callable=PropertyMock) as mock_files:
#         mock_files.return_value = []

#         # Run command
#         result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
#         assert result.exit_code == 0

#     # Verify output -- no lost files
#     _, err = capfd.readouterr()
#     assert "Searching for lost files in project" not in err
#     assert "No project specified, searching for lost files in all units." in err
#     for u in models.Unit.query.all():
#         assert f"Listing lost files in unit: {u.public_id}" in err
#         for p in u.projects:
#             if u.public_id == unit_no_sto4_endpoint_id:
#                 assert f"One or more sto4 variables are missing for unit {u.public_id}." in err
#                 assert f"Safespring location for project '{p.public_id}': sto2" not in err
#                 assert f"Safespring location for project '{p.public_id}': sto4" not in err
#             else:
#                 assert f"Safespring location for project '{p.public_id}': sto2" not in err
#                 assert f"Safespring location for project '{p.public_id}': sto4" in err
#     assert f"No lost files for unit '{u.public_id}'" in err
#     # ---------------------------------------------------------------------------------------


# def test_list_lost_files_missing_in_s3_in_project(client, cli_runner, boto3_session, capfd):
#     """flask lost-files ls: project specified, lost files in s3."""
#     # Run command
#     result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["ls"])
#     assert result.exit_code == 0

#     # Verify output
#     _, err = capfd.readouterr()
#     # All files should be in db but not in s3
#     for u in models.Unit.query.all():
#         num_files: int = 0
#         for p in u.projects:
#             num_files += len(p.files)
#             for f in p.files:
#                 assert (
#                     f"Entry {f.name_in_bucket} ({p.public_id}, {u}) not found in S3 (but found in db)"
#                     in err
#                 )
#                 assert (
#                     f"Entry {f.name_in_bucket} ({p.public_id}, {u}) not found in database (but found in s3)"
#                     not in err
#                 )
#         assert f"Lost files for unit: {u.public_id}\t\tIn DB but not S3: {num_files}\tIn S3 but not DB: 0\tProject errors: 0\n"


# lost_files_s3_db -- add_missing_bucket


def test_add_missing_bucket_no_project(client, cli_runner):
    """flask lost-files add-missing-bucket: no project specified (required)."""
    # Run command
    result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["add-missing-bucket"])

    # Get output from result and verify that help message printed
    assert result.exit_code == 2
    assert "Missing option '--project-id' / '-p'." in result.stdout


def test_add_missing_bucket_project_nonexistent(client, cli_runner, capfd):
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


def test_add_missing_bucket_project_inactive(client, cli_runner, capfd):
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


def test_add_missing_bucket_not_missing(client, cli_runner, boto3_session, capfd):
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


# # lost_files_s3_db -- delete_lost_files


# def test_delete_lost_files_no_project(client, cli_runner):
#     """flask lost-files delete: no project specified (required)."""
#     # Run command
#     result: click.testing.Result = cli_runner.invoke(lost_files_s3_db, ["delete"])

#     # Get output from result and verify that help message printed
#     assert result.exit_code == 2
#     assert "Missing option '--project-id' / '-p'." in result.stdout


# def test_delete_lost_files_project_nonexistent(client, cli_runner, capfd):
#     """flask lost-files delete: no such project --> print out error."""
#     # Project -- doesn't exist
#     project_id: str = "nonexistentproject"
#     assert not models.Project.query.filter_by(public_id=project_id).one_or_none()

#     # Run command
#     result: click.testing.Result = cli_runner.invoke(
#         lost_files_s3_db, ["delete", "--project-id", project_id]
#     )
#     assert result.exit_code == 1

#     # Verify output
#     _, err = capfd.readouterr()
#     assert f"No such project: '{project_id}'" in err


# def test_delete_lost_files_deleted(client, cli_runner, boto3_session, capfd):
#     """flask lost-files delete: project specified and exists --> deleted files ok."""
#     # Get project
#     project: models.Project = models.Project.query.first()
#     assert project
#     num_project_files = len(project.files)
#     assert num_project_files > 0

#     # Run command
#     result: click.testing.Result = cli_runner.invoke(
#         lost_files_s3_db, ["delete", "--project-id", project.public_id]
#     )
#     assert result.exit_code == 0

#     # Verify output - files deleted
#     _, err = capfd.readouterr()
#     assert f"Files deleted from S3: 0" in err
#     assert f"Files deleted from DB: {num_project_files}" in err


# def test_delete_lost_files_sqlalchemyerror(client, cli_runner, boto3_session, capfd):
#     """flask lost-files delete: sqlalchemyerror during deletion."""
#     # Imports
#     from tests.api.test_project import mock_sqlalchemyerror

#     # Get project
#     project: models.Project = models.Project.query.first()
#     assert project
#     num_project_files = len(project.files)
#     assert num_project_files > 0

#     # Mock commit --> no delete
#     with patch("dds_web.db.session.commit", mock_sqlalchemyerror):
#         # Run command
#         result: click.testing.Result = cli_runner.invoke(
#             lost_files_s3_db, ["delete", "--project-id", project.public_id]
#         )
#         assert result.exit_code == 1

#     # Verify output - files deleted
#     _, err = capfd.readouterr()
#     assert "Unable to delete the database entries" in err
#     assert f"Files deleted from S3: 0" not in err
#     assert f"Files deleted from DB: 0" not in err


# # usage = 0 --> check log
# def test_monitor_usage_no_usage(client, cli_runner, capfd):
#     """If a unit has no uploaded data, there's no need to do the calculations or send email warning."""
#     # Mock the size property of the Unit table
#     with patch("dds_web.database.models.Unit.size", new_callable=PropertyMock) as mock_size:
#         mock_size.return_value = 0  # Test size = 0
#         # Mock emails - only check if function call
#         with patch.object(flask_mail.Mail, "send") as mock_mail_send:
#             # Run command
#             _: click.testing.Result = cli_runner.invoke(monitor_usage)
#             # Verify no email has been sent and stoud contains logging info
#             assert mock_mail_send.call_count == 0
#     # Logging ends up in stderr
#     _, err = capfd.readouterr()
#     for unit in models.Unit.query.all():
#         assert f"{unit.name} usage: 0 bytes. Skipping percentage calculation." in err


# # percentage below warning level --> check log + no email
# def test_monitor_usage_no_email(client, cli_runner, capfd):
#     """No email should be sent if the usage is below the warning level."""
#     # Define quota
#     quota_in_test: int = 1e14
#     assert quota_in_test == 100000000000000
#     for unit in models.Unit.query.all():
#         unit.quota = quota_in_test
#         unit.warning_level = 0.8
#     db.session.commit()

#     # Mock the size property of the Unit table
#     with patch("dds_web.database.models.Unit.size", new_callable=PropertyMock) as mock_size:
#         mock_size.return_value = 0.7 * quota_in_test
#         # Mock emails - only check if function call
#         with patch.object(flask_mail.Mail, "send") as mock_mail_send:
#             # Run command
#             _: click.testing.Result = cli_runner.invoke(monitor_usage)
#             # Verify no email has been sent and stoud contains logging info
#             assert mock_mail_send.call_count == 0
#     # Logging ends up in stderr
#     _, err = capfd.readouterr()
#     for unit in models.Unit.query.all():
#         assert f"Monitoring the usage for unit '{unit.name}' showed the following:\n" in err
#         assert (
#             f"A SciLifeLab Unit is approaching the allocated data quota.\nAffected unit: {unit.name}\n"
#             not in err
#         )


# # percentage above warning level --> check log + email sent
# def test_monitor_usage_warning_sent(client, cli_runner, capfd):
#     """An email should be sent if the usage is above the warning level."""
#     # Define quota
#     quota_in_test: int = 1e14
#     assert quota_in_test == 100000000000000
#     for unit in models.Unit.query.all():
#         unit.quota = quota_in_test
#         unit.warning_level = 0.8
#     db.session.commit()

#     # Mock the size property of the Unit table
#     with patch("dds_web.database.models.Unit.size", new_callable=PropertyMock) as mock_size:
#         mock_size.return_value = 0.9 * quota_in_test
#         # Mock emails - only check if function call
#         with patch.object(flask_mail.Mail, "send") as mock_mail_send:
#             # Run command
#             _: click.testing.Result = cli_runner.invoke(monitor_usage)
#             # Verify no email has been sent and stoud contains logging info
#             assert mock_mail_send.call_count == 2  # 2 because client and cli_runner both run

#     _, err = capfd.readouterr()
#     for unit in models.Unit.query.all():
#         assert (
#             f"A SciLifeLab Unit is approaching the allocated data quota.\nAffected unit: {unit.name}\n"
#             in err
#         )


# # set_available_to_expired


# def test_set_available_to_expired(client, cli_runner):
#     units: List = db.session.query(models.Unit).all()
#     # Set project statuses to Available
#     # and deadline to now to be able to test cronjob functionality
#     for unit in units:
#         for project in unit.projects:
#             for status in project.project_statuses:
#                 status.deadline = current_time() - timedelta(weeks=1)
#                 status.status = "Available"

#     i: int = 0
#     for unit in units:
#         i += len(
#             [
#                 project
#                 for project in unit.projects
#                 if project.current_status == "Available"
#                 and project.current_deadline <= current_time()
#             ]
#         )
#     assert i == 6

#     cli_runner.invoke(set_available_to_expired)

#     units: List = db.session.query(models.Unit).all()

#     i: int = 0
#     j: int = 0
#     for unit in units:
#         i += len([project for project in unit.projects if project.current_status == "Available"])
#         j += len([project for project in unit.projects if project.current_status == "Expired"])

#     assert i == 0
#     assert j == 6


# # set_expired_to_archived


# @mock.patch("boto3.session.Session")
# def test_set_expired_to_archived(_: MagicMock, client, cli_runner):
#     units: List = db.session.query(models.Unit).all()

#     for unit in units:
#         for project in unit.projects:
#             for status in project.project_statuses:
#                 status.deadline = current_time() - timedelta(weeks=1)
#                 status.status = "Expired"

#     i: int = 0
#     for unit in units:
#         i += len([project for project in unit.projects if project.current_status == "Expired"])
#     assert i == 6

#     cli_runner.invoke(set_expired_to_archived)

#     units: List = db.session.query(models.Unit).all()

#     i: int = 0
#     j: int = 0
#     for unit in units:
#         i += len([project for project in unit.projects if project.current_status == "Expired"])
#         j += len([project for project in unit.projects if project.current_status == "Archived"])

#     assert i == 0
#     assert j == 6


# # delete invites


# def test_delete_invite(client, cli_runner):
#     assert len(db.session.query(models.Invite).all()) == 2
#     cli_runner.invoke(delete_invites)
#     assert len(db.session.query(models.Invite).all()) == 1


# def test_delete_invite_timestamp_issue(client, cli_runner):
#     """Test that the delete_invite cronjob deletes invites with '0000-00-00 00:00:00' timestamp."""
#     assert len(db.session.query(models.Invite).all()) == 2
#     invites = db.session.query(models.Invite).all()
#     for invite in invites:
#         invite.created_at = "0000-00-00 00:00:00"
#     db.session.commit()
#     cli_runner.invoke(delete_invites)
#     assert len(db.session.query(models.Invite).all()) == 0


# # quarterly usage


# def test_quarterly_usage(client, cli_runner):
#     """Test the quarterly_usage cron job."""
#     cli_runner.invoke(quarterly_usage)


# # reporting units and users


# def test_collect_stats(client, cli_runner, fs: FakeFilesystem):
#     """Test that the reporting is giving correct values."""
#     from dds_web.database.models import (
#         Unit,
#         UnitUser,
#         ResearchUser,
#         SuperAdmin,
#         User,
#         Reporting,
#         Project,
#         ProjectUsers,
#         Version,
#     )
#     from dds_web.utils import bytehours_in_last_month, page_query, calculate_bytehours
#     import dds_web.utils

#     def verify_reporting_row(row, time_date):
#         """Verify correct values in reporting row."""
#         assert row.date.date() == datetime.date(time_date)
#         assert row.unit_count == Unit.query.count()
#         assert row.researcher_count == ResearchUser.query.count()
#         assert row.unit_personnel_count == UnitUser.query.filter_by(is_admin=False).count()
#         assert row.unit_admin_count == UnitUser.query.filter_by(is_admin=True).count()
#         assert row.superadmin_count == SuperAdmin.query.count()
#         assert row.total_user_count == User.query.count()
#         assert row.total_user_count == sum(
#             [
#                 row.researcher_count,
#                 row.unit_personnel_count,
#                 row.unit_admin_count,
#                 row.superadmin_count,
#             ]
#         )
#         assert row.project_owner_unique_count == (
#             ProjectUsers.query.filter_by(owner=True)
#             .with_entities(ProjectUsers.user_id)
#             .distinct()
#             .count()
#         )
#         assert row.total_project_count == Project.query.count()
#         assert row.active_project_count == Project.query.filter_by(is_active=True).count()
#         assert row.inactive_project_count == Project.query.filter_by(is_active=False).count()
#         assert row.total_project_count == sum(
#             [
#                 row.active_project_count,
#                 row.inactive_project_count,
#             ]
#         )
#         assert row.tb_stored_now == round(
#             sum(proj.size for proj in Project.query) / 1000000000000, 2
#         )
#         assert row.tb_uploaded_since_start == round(
#             sum(version.size_stored for version in dds_web.utils.page_query(Version.query))
#             / 1000000000000,
#             2,
#         )
#         assert row.tbhours == round(
#             sum(bytehours_in_last_month(version=version) for version in page_query(Version.query))
#             / 1e12,
#             2,
#         )
#         assert row.tbhours_since_start == round(
#             sum(
#                 calculate_bytehours(
#                     minuend=version.time_deleted or time_date,
#                     subtrahend=version.time_uploaded,
#                     size_bytes=version.size_stored,
#                 )
#                 for version in page_query(Version.query)
#             )
#             / 1e12,
#             2,
#         )

#     # Verify that there are no reporting rows
#     assert Reporting.query.count() == 0

#     # Run successful command - new row should be created
#     first_time = datetime(year=2022, month=12, day=10, hour=10, minute=54, second=10)
#     with freezegun.freeze_time(first_time):
#         # Run scheduled job now
#         with mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
#             result: click.testing.Result = cli_runner.invoke(collect_stats)
#             assert not result.exception, "Raised an unwanted exception."
#             assert mock_mail_send.call_count == 0

#     # Verify that there's now a reporting row
#     assert Reporting.query.count() == 1
#     row = Reporting.query.first()
#     verify_reporting_row(row=row, time_date=first_time)

#     # Check that an exception is raised if the command is run on the same day
#     with freezegun.freeze_time(first_time):
#         # Run scheduled job now
#         with mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
#             # with pytest.raises(Exception) as err:
#             result: click.testing.Result = cli_runner.invoke(collect_stats)
#             assert result.exception, "Did not raise exception."
#             assert "Duplicate entry" in str(result.exception)
#             assert mock_mail_send.call_count == 1

#     # Verify that the next day works
#     second_time = datetime(year=2022, month=12, day=11, hour=10, minute=54, second=10)
#     with freezegun.freeze_time(second_time):
#         # Run scheduled job now
#         with mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
#             result: click.testing.Result = cli_runner.invoke(collect_stats)
#             assert not result.exception, "Raised an unwanted exception."
#             assert mock_mail_send.call_count == 0

#     # Verify that there's now a reporting row
#     assert Reporting.query.count() == 2
#     reporting_rows = Reporting.query.all()
#     for row in reporting_rows:
#         verify_reporting_row(row=row, time_date=first_time if row.id == 1 else second_time)
