"""Tests for database migrations."""

import pathlib
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy_utils import create_database, drop_database, database_exists

from dds_web import create_app, db

ALEMBIC_CFG_PATH = pathlib.Path("migrations") / "alembic.ini"

@pytest.fixture
def migration_app():
    """Fixture to create a fresh database for migration tests.
    
    1. Spin up empty database
    2. Run migrations
    3. Drop database again
    """
    # Use a test database URI
    uri = "mysql+pymysql://root:pass@db/DeliverySystemMigrationTest"

    # Ensure new database
    if database_exists(uri):
        drop_database(uri)
    create_database(uri)

    # Create app with the test database
    app = create_app(testing=True, database_uri=uri)
    with app.app_context():
        yield app, uri

    # Teardown: drop the test database
    drop_database(uri)


def test_full_upgrade_and_downgrade(migration_app):
    """Test upgrade and downgrade of all migrations."""
    app, uri = migration_app
    cfg = Config(str(ALEMBIC_CFG_PATH))
    cfg.set_main_option("sqlalchemy.url", uri)

    # upgrade to latest revision
    command.upgrade(cfg, "head")

    # downgrade back to base
    command.downgrade(cfg, "base")

    # upgrade again to ensure reversibility
    command.upgrade(cfg, "head")

def test_models_match_schema(migration_app):
    """Verify that no changes are detected between models and no migration is needed."""
    app, uri = migration_app
    cfg = Config(str(ALEMBIC_CFG_PATH))
    cfg.set_main_option("sqlalchemy.url", uri)

    # running `db migrate` should yield "No changes in schema detected"
    runner = app.test_cli_runner()
    result = runner.invoke(args=["db", "migrate"])
    assert "No changes in schema detected" in result.output
