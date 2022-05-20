from dds_web import fill_db_wrapper
import click.testing
import pytest
from pytest_mock import MockFixture

@pytest.fixture
def runner() -> click.testing.CliRunner:
    return click.testing.CliRunner()

def test_fill_db_wrapper_production(client, runner) -> None:
    """"""
    result = runner.invoke(fill_db_wrapper, ["production"])
    assert result.exit_code == 1

def test_fill_db_wrapper_devsmall(client, runner) -> None:
    """"""
    result = runner.invoke(fill_db_wrapper, ["dev-small"])
    assert result.exit_code == 1

def test_fill_db_wrapper_devbig(client, runner) -> None:
    result = runner.invoke(fill_db_wrapper, ["dev-big"])
    assert result.exit_code == 1
    