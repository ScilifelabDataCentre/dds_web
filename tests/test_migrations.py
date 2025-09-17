"""Tests verifying that the database migration versions work as intended."""

# IMPORTS ##########################################################################
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from .conftest import schema_only_database

# TESTS ############################################################################

def test_migrations_apply_latest_schema(schema_only_database):
    """Verify migrations upgraded the schema-only database to the latest head."""
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    alembic_cfg = Config(str(migrations_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    head_revision = ScriptDirectory.from_config(alembic_cfg).get_current_head()

    engine = create_engine(schema_only_database)
    try:
        inspector = inspect(engine)
        assert "researchuser" in inspector.get_table_names()

        with engine.connect() as connection:
            result = connection.execute(text("SELECT version_num FROM alembic_version"))
            current_revision = result.scalar_one()
            assert current_revision == head_revision

            user_count = connection.execute(text("SELECT COUNT(*) FROM researchuser")).scalar_one()
            assert user_count == 0
    finally:
        engine.dispose()