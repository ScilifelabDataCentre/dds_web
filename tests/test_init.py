from dds_web import fill_db_wrapper, create_new_unit, update_uploaded_file_with_log
import click.testing
import pytest
from dds_web import db
from dds_web.database import models
from pytest_mock import MockFixture
import typing

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

def test_fill_db_wrapper_devbig(client, runner) -> None:
    """Run init-db with the dev-big argument."""
    result: click.testing.Result = runner.invoke(fill_db_wrapper, ["dev-big"])
    assert result.exit_code == 1

# create_new_unit

correct_unit: typing.Dict = {"name": "newname","public_id": "newpublicid", "external_display_name": "newexternaldisplay", "contact_email": "newcontact@mail.com", "internal_ref": "newinternalref", "safespring_endpoint": "newsafespringendpoint", "safespring_access": "newsafespringaccess", "safespring_secret": "newsafespringsecret", "days_in_available": 45, "days_in_expired": 15,}
def test_create_new_unit_public_id_too_long(client, runner) -> None:
    """Create new unit, public_id too long."""
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "public"*10
    command: typing.List = [f"--{key} {val}" for key, val in incorrect_unit.items()]
    result: click.testing.Result = runner.invoke(create_new_unit, [" ".join(command)])
    assert result.output == "The 'public_id' can be a maximum of 50 characters"
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

def test_create_new_unit_public_id_incorrect_characters(client, runner) -> None:
    """Create new unit, public_id has invalid characters (here _)."""
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "new_public_id"
    command: typing.List = [f"--{key} {val}" for key, val in incorrect_unit.items()]
    result: click.testing.Result = runner.invoke(create_new_unit, [" ".join(command)])
    assert result.output == "The 'public_id' can only contain letters, numbers, dots (.) and hyphens (-)."
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

def test_create_new_unit_public_id_starts_with_dot(client, runner) -> None:
    """Create new unit, public_id starts with invalid character (. or -)."""
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = ".newpublicid"
    command: typing.List = [f"--{key} {val}" for key, val in incorrect_unit.items()]
    result: click.testing.Result = runner.invoke(create_new_unit, [" ".join(command)])
    assert result.output == "The 'public_id' must begin with a letter or number."
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

    incorrect_unit["public_id"] = "-newpublicid"
    command: typing.List = [f"--{key} {val}" for key, val in incorrect_unit.items()]
    result: click.testing.Result = runner.invoke(create_new_unit, [" ".join(command)])
    assert result.output == "The 'public_id' must begin with a letter or number."
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

def test_create_new_unit_public_id_too_many_dots(client, runner) -> None:
    """Create new unit, public_id has invalid number of dots."""
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "new.public..id"
    command: typing.List = [f"--{key} {val}" for key, val in incorrect_unit.items()]
    result: click.testing.Result = runner.invoke(create_new_unit, [" ".join(command)])
    assert result.output == "The 'public_id' should not contain more than two dots."
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

def test_create_new_unit_public_id_invalid_start(client, runner) -> None:
    """Create new unit, public_id starts with prefix."""
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "xn--newpublicid"
    command: typing.List = [f"--{key} {val}" for key, val in incorrect_unit.items()]
    result: click.testing.Result = runner.invoke(create_new_unit, [" ".join(command)])
    assert result.output == "The 'public_id' cannot begin with the 'xn--' prefix."
    assert not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()

def test_create_new_unit_success(client, runner) -> None:
    """Create new unit, public_id starts with prefix."""
    command: typing.List = [f"--{key} {val}" for key, val in correct_unit.items()]
    result: click.testing.Result = runner.invoke(create_new_unit, [" ".join(command)])
    assert result.output == f"Unit '{correct_unit['name']}' created"
    assert db.session.query(models.Unit).filter(models.Unit.name == correct_unit["name"]).all()

# Update uploaded file with log 

def test_update_uploaded_file_with_log_nonexisting_project(client, runner) -> None:
    """Add file info to non existing project."""
    command: str = "--project projectdoesntexist --path-to-log-file somefile"
    result: click.testing.Result = runner.invoke(update_uploaded_file_with_log, [command])
    assert result.exit_code == 1
    assert "AssertionError" in result.output