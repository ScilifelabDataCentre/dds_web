from dds_web import fill_db_wrapper
import click.testing
import pytest
from pytest_mock import MockFixture

@pytest.fixture
def runner() -> click.testing.CliRunner:
    return click.testing.CliRunner()

def test_fill_db_wrapper(client, runner):
    """"""
    result = runner.invoke(fill_db_wrapper, ["production"])
    assert result.exit_code == 1