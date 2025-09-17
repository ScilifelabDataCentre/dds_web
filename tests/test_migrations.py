"""Tests verifying that the database migration versions work as intended."""

# IMPORTS ##########################################################################
from pathlib import Path
import flask_migrate

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, Table, create_engine, func, inspect, select

from dds_web import create_app, db

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
        # ``researchusers`` is created by the migrations and should remain empty until
        # filling the database --> good test for the expected schema.
        assert inspector.has_table("researchusers")

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
            researchusers = Table("researchusers", MetaData(), autoload_with=connection)
            user_count = connection.execute(
                select(func.count()).select_from(researchusers)
            ).scalar_one()
            assert user_count == 0
    finally:
        engine.dispose()


def test_migrations_can_downgrade_to_base(migrated_database):
    """Downgrade and upgrade migrations on a temporary database."""

    # Locate the migrations directory starting from this file's location
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"

    # Find the Alembic configuration file
    alembic_cfg = Config(str(migrations_dir / "alembic.ini"))

    # Override the script_location to point to our migrations directory
    alembic_cfg.set_main_option("script_location", str(migrations_dir))

    # Get the current head revision from the migrations
    head_revision = ScriptDirectory.from_config(alembic_cfg).get_current_head()

    # Connect to the throwaway database
    engine = create_engine(migrated_database)
    try:
        # Confirm the throwaway database starts at the head revision.
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            assert context.get_current_revision() == head_revision

        # Downgrade all migrations to the base revision.
        app = create_app(testing=True, database_uri=migrated_database)
        with app.test_request_context():
            with app.test_client():
                try:
                    flask_migrate.downgrade(revision="base")
                finally:
                    db.session.remove()
                    db.engine.dispose()

        # Verify that the downgrade removed all tables and that the current version is none
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            assert context.get_current_revision() is None

        inspector = inspect(engine)
        assert not inspector.has_table("researchusers")

        # Upgrade back to head to confirm we can recover the schema.
        app = create_app(testing=True, database_uri=migrated_database)
        
        with app.test_request_context():
            with app.test_client():
                try:
                    flask_migrate.upgrade()
                finally:
                    db.session.remove()
                    db.engine.dispose()

        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            assert context.get_current_revision() == head_revision

        inspector = inspect(engine)
        assert inspector.has_table("researchusers")
    finally:
        engine.dispose()
