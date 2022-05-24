from unittest import result

from click import command
from dds_web import fill_db_wrapper, create_new_unit, update_uploaded_file_with_log
import click.testing
import pytest
from dds_web import db
from dds_web.database import models
from pytest_mock import MockFixture
import typing
from pyfakefs.fake_filesystem import FakeFilesystem
import os

@pytest.fixture
def runner() -> click.testing.CliRunner:
    return click.testing.CliRunner()

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

correct_unit: typing.Dict = {"name": "newname","public_id": "newpublicid", "external_display_name": "newexternaldisplay", "contact_email": "newcontact@mail.com", "internal_ref": "newinternalref", "safespring_endpoint": "newsafespringendpoint", "safespring_name": "newsafespringname", "safespring_access": "newsafespringaccess", "safespring_secret": "newsafespringsecret", "days_in_available": 45, "days_in_expired": 15,}

def test_create_new_unit_public_id_too_long(client, runner) -> None:
    """Create new unit, public_id too long."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "public"*10

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    assert "The 'public_id' can be a maximum of 50 characters" in result.output
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

def test_create_new_unit_public_id_incorrect_characters(client, runner) -> None:
    """Create new unit, public_id has invalid characters (here _)."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "new_public_id"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit,command_options)
    assert result.output == "The 'public_id' can only contain letters, numbers, dots (.) and hyphens (-)."
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

def test_create_new_unit_public_id_starts_with_dot(client, runner) -> None:
    """Create new unit, public_id starts with invalid character (. or -)."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = ".newpublicid"
    
    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    assert result.output == "The 'public_id' must begin with a letter or number."
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

    # Change public_id again
    incorrect_unit["public_id"] = "-newpublicid"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    assert result.output == "The 'public_id' must begin with a letter or number."
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

def test_create_new_unit_public_id_too_many_dots(client, runner) -> None:
    """Create new unit, public_id has invalid number of dots."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "new.public..id"
    
    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command 
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    assert result.output == "The 'public_id' should not contain more than two dots."
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

def test_create_new_unit_public_id_invalid_start(client, runner) -> None:
    """Create new unit, public_id starts with prefix."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "xn--newpublicid"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command 
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    assert result.output == "The 'public_id' cannot begin with the 'xn--' prefix."
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

def test_create_new_unit_success(client, runner) -> None:
    """Create new unit, public_id starts with prefix."""
    # Get command options
    command_options = create_command_options_from_dict(options=correct_unit)

    # Run command 
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    assert result.output == f"Unit '{correct_unit['name']}' created"
    assert db.session.query(models.Unit).filter(models.Unit.name == correct_unit["name"]).all()

# Update uploaded file with log 

def test_update_uploaded_file_with_log_nonexisting_project(client, runner) -> None:
    """Add file info to non existing project."""
    # Create command options
    command_options: typing.List = ["--project", "projectdoesntexist", "--path-to-log-file", "somefile"]
    
    # Run command 
    result: click.testing.Result = runner.invoke(update_uploaded_file_with_log, command_options)
    assert result.exit_code == 1
    assert "AssertionError" in result.output

def test_update_uploaded_file_with_log_nonexisting_file(client, runner, fs: FakeFilesystem) -> None:
    """Attempt to read file which does not exist."""
    # Verify that fake file does not exist
    non_existent_log_file: str = "this_is_not_a_file.json"
    assert not os.path.exists(non_existent_log_file)

    # Create command options
    command_options: typing.List = ["--project", "projectdoesntexist", "--path-to-log-file", non_existent_log_file]
    
    # Run command 
    result: click.testing.Result = runner.invoke(update_uploaded_file_with_log, command_options)
    assert result.exit_code == 1

