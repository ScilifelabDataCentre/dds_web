"""Tests verifying that the database migration versions work as intended."""

# IMPORTS ##########################################################################
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, Table, create_engine, func, inspect, select

# TESTS ############################################################################


def test_migrations_apply_latest_schema(schema_only_database):
    """Verify migrations upgraded the schema-only database to the latest head."""

    # Locate the migrations directory starting from this file's location
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"

    # Find the Alembic configuration file
    alembic_cfg = Config(str(migrations_dir / "alembic.ini"))

    # Override the script_location to point to our migrations directory
    alembic_cfg.set_main_option("script_location", str(migrations_dir))

    # Get the current head revision from the migrations
    head_revision = ScriptDirectory.from_config(alembic_cfg).get_current_head()

    # Connect to the schema-only database and verify the current revision
    engine = create_engine(schema_only_database)
    try:
        inspector = inspect(engine)
        # ``researchuser`` is created by the migrations and should remain empty until
        # filling the database --> good test for the expected schema.
        assert inspector.has_table("researchuser")

        with engine.connect() as connection:
            # Compare correct latest version
            context = MigrationContext.configure(connection)
            current_revision = context.get_current_revision()
            assert current_revision == head_revision

            # Count number of rows in researchusers table -- should be 0
            # Plain SQLAlchemy because the schema_only_database fixture doesn’t
            # spin up a Flask application context etc
            # This way --> test talks directly to the fixture database and
            # keep the focus on verifying the migrations in isolation.
            researchuser = Table("researchuser", MetaData(), autoload_with=connection)
            user_count = connection.execute(
                select(func.count()).select_from(researchuser)
            ).scalar_one()
            assert user_count == 0
    finally:
        engine.dispose()
