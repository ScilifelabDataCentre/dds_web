"""Tests verifying that the database migration versions work as intended."""

# IMPORTS ##########################################################################
from pathlib import Path
import datetime
import flask_migrate
import pytest
import sqlalchemy

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, Table, create_engine, func, inspect, select
from sqlalchemy.dialects import mysql
from sqlalchemy.sql import sqltypes

from dds_web import create_app, db

# HELPERS ############################################################################


def _assert_projects_after_downgrade(connection, context):
    """Verify that a downgrade has filled the project columns with the correct values.

    The context in this case is the data before downgrade.
    Needs to be called context in order for rollbacks to work,
    and for the updates to the shared contects object to stay.
    """
    table = _get_table(connection=connection, name="projects")

    # Verify that non_sensitive is no longer a valid column name
    assert "is_sensitive" in table.c
    assert "non_sensitive" not in table.c

    # Verify that the bool data after downgrade is the oposite of before downgrade
    rows = connection.execute(select(table.c.bucket, table.c.is_sensitive)).all()
    expected = {bucket: not value for bucket, value in context["expected_non_sensitive"].items()}
    assert {row.bucket: bool(row.is_sensitive) for row in rows} == expected


def _assert_projects_after_upgrade(connection, context):
    """Verify that an upgrade has filled the project columns with the correct values.

    The context in this case is the data before upgrade.
    Needs to be called context in order for rollbacks to work,
    and for the updates to the shared contects object to stay.
    """
    table = _get_table(connection=connection, name="projects")

    # is_sensitive is no longer a valid column name
    assert "non_sensitive" in table.c
    assert "is_sensitive" not in table.c

    # Verify that the bool data after upgrade is the oposite of before upgrade
    expected = {bucket: not bool(flag) for bucket, flag in context["projects"].items()}
    rows = connection.execute(select(table.c.bucket, table.c.non_sensitive)).all()
    assert {row.bucket: bool(row.non_sensitive) for row in rows} == expected

    # Mutate dictionary in place -- extra data stays on shared context object
    # and is available when downgrade assertion runs
    context["expected_non_sensitive"] = {row.bucket: bool(row.non_sensitive) for row in rows}


def _assert_unit_contact_email_after_downgrade(connection, context):
    """Verify that a downgrade has set the unit contact_email as the correct type,
    and filled it with the correct values.

    The context in this case is the data before downgrade.
    Needs to be called context in order for rollbacks to work,
    and for the updates to the shared contects object to stay.
    """
    table = _get_table(connection=connection, name="units")

    # Verify that the contact_email column is nullable
    assert table.c.contact_email.nullable is True

    # Verify that the contact_email value is set to the default
    result = connection.execute(
        select(table.c.contact_email).where(table.c.public_id == context["public_id"])
    ).one()
    assert result.contact_email == "delivery@scilifelab.se"


def _assert_unit_contact_email_after_upgrade(connection, context):
    """Verify that an upgrade has set the unit contact_email as correct type,
    and filled it with the correct value.

    The context in this case is the data before upgrade.
    Needs to be called context in order for rollbacks to work,
    and for the updates to the shared contects object to stay.
    """
    table = _get_table(connection=connection, name="units")

    # Verify that the contact_email is now not nullable
    assert table.c.contact_email.nullable is False

    # Verify that the contact_email value is set to the default
    result = connection.execute(
        select(table.c.contact_email).where(table.c.public_id == context["public_id"])
    ).one()
    assert result.contact_email == "delivery@scilifelab.se"


def _assert_unit_quota_after_downgrade(connection, context):
    """Verify that a downgrade has removed the unit table columns quota and warning_level."""
    _ = context  # context is intentionally unused, but want keyword argument in function calls

    table = _get_table(connection=connection, name="units")

    # Verify that there are no columns called quota or warning_level in the unit table
    assert "quota" not in table.c
    assert "warning_level" not in table.c


def _assert_unit_quota_after_upgrade(connection, context):
    """Verify that an upgrade has filled the unit columns quota and warning_level with the correct values.

    The context in this case is the data before upgrade.
    Needs to be called context in order for rollbacks to work,
    and for the updates to the shared contects object to stay.
    """
    table = _get_table(connection=connection, name="units")

    # Verify that there is a quota and warning_level column in the units table
    assert "quota" in table.c
    assert "warning_level" in table.c

    # Verify that column values have been filled with defaults
    row = connection.execute(
        select(table.c.quota, table.c.warning_level).where(
            table.c.public_id == context["public_id"]
        )
    ).one()
    assert row.quota == 100 * (10**12)
    assert row.warning_level == pytest.approx(0.8)


def _assert_user_active_after_downgrade(connection, context):
    """Verify that a downgrade has filled the user column active with the correct type and value.

    The context in this case is the data before downgrade.
    Needs to be called context in order for rollbacks to work,
    and for the updates to the shared contects object to stay.
    """
    table = _get_table(connection=connection, name="users")

    # Verify that active column is nullable
    assert table.c.active.nullable is True

    # Verify that active column value for users is a bool
    result = connection.execute(
        select(table.c.active).where(table.c.username == context["username"])
    ).one()
    assert result.active == 0 # sa.Boolean actually stored as TINYINT in mysql --> 0 not False


def _assert_user_active_after_upgrade(connection, context):
    """Verify that an upgrade has filled the user column active with the correct type and value.

    The context in this case is the data before upgrade.
    Needs to be called context in order for rollbacks to work,
    and for the updates to the shared contects object to stay.
    """
    table = _get_table(connection=connection, name="users")

    # Active column should not be nullable
    assert table.c.active.nullable is False

    # Verify that active column value for users is a bool
    result = connection.execute(
        select(table.c.active).where(table.c.username == context["username"])
    ).one()
    assert result.active == 0 # sa.Boolean actually stored as TINYINT in mysql --> 0 not False


def _default_value_for(column: sqlalchemy.Column) -> object:
    """Return a generic value compatible with the given column."""

    if isinstance(column.type, (sqltypes.Boolean, mysql.TINYINT)):
        return False
    if isinstance(
        column.type, (sqltypes.Integer, sqltypes.BigInteger, mysql.INTEGER, mysql.BIGINT)
    ):
        return 0
    if isinstance(column.type, (sqltypes.Numeric, sqltypes.Float, mysql.DECIMAL, mysql.FLOAT)):
        return 0
    if isinstance(column.type, sqltypes.DateTime):
        return datetime.datetime.utcnow()
    if isinstance(
        column.type,
        (
            sqltypes.LargeBinary,
            sqltypes._Binary,
            mysql.BINARY,
            mysql.VARBINARY,
        ),
    ):
        length = getattr(column.type, "length", None) or 1
        return b"x" * length
    return f"default_{column.name}"


def _get_table(connection, name: str) -> Table:
    """Return the specified table."""
    metadata = MetaData()
    return Table(name, metadata, autoload_with=connection)


def _insert_with_defaults(connection, table: Table, values: dict) -> None:
    """Inspect metadata and fills in any non-nullable columns with dummy values."""
    row = {}

    for column in table.columns:
        # No dummy values when handled automatically by database
        # or if column specified in function call
        if column.primary_key and column.autoincrement:
            continue
        if column.name in values:
            continue

        # Get default value where applicable
        if not column.nullable and column.server_default is None and column.default is None:
            row[column.name] = _default_value_for(column=column)

    # Include user specified columns and data (non defaults)
    row.update(values)

    # Insert data into database
    connection.execute(table.insert(), [row])


def _run_migration(app, migration_func, revision):
    """Wrap migration_func (upgrade or downgrade) in application request context
    in order for Alembic to operate correctly.
    """
    with app.test_request_context():
        with app.test_client():
            try:
                # Run migration function
                migration_func(revision=revision)
            finally:
                # Tear down session after migration function finished
                # to avoid leaked connections
                db.session.remove()
                db.engine.dispose()


def _setup_projects(connection):
    """Insert base level data into projects table."""
    table = _get_table(connection=connection, name="projects")

    # Base project info regarding sentisivity
    base_rows = [
        {
            "bucket": "bucket_sensitive_false",
            "is_active": True,
            "is_sensitive": 0,
            "title": "Public",
        },
        {
            "bucket": "bucket_sensitive_true",
            "is_active": True,
            "is_sensitive": 1,
            "title": "Sensitive",
        },
    ]

    # Insert base project info into table
    for row in base_rows:
        _insert_with_defaults(connection=connection, table=table, values=row)

    return {"projects": {row["bucket"]: row["is_sensitive"] for row in base_rows}}


def _setup_unit_without_contact_email(connection):
    """Insert base level data into units table, with no contact email."""
    table = _get_table(connection=connection, name="units")

    # Insert unit info into database
    public_id = "unit-without-contact-email"
    _insert_with_defaults(
        connection,
        table,
        {
            "public_id": public_id,
            "name": "Contact Email Unit",
            "external_display_name": "Contact Email Unit",
            "internal_ref": "contact-email",
            "contact_email": None,
        },
    )
    return {"public_id": public_id}


def _setup_unit_without_quota(connection):
    """Insert base level data into units tabel, with no quota."""
    table = _get_table(connection=connection, name="units")

    # Insert unit info into database
    public_id = "unit-without-quota"
    _insert_with_defaults(
        connection=connection,
        table=table,
        values={
            "public_id": public_id,
            "name": "Quota Test Unit",
            "external_display_name": "Quota Test Unit",
            "internal_ref": "quota-test",
        },
    )

    return {"public_id": public_id}


def _setup_user_with_null_active(connection):
    """Insert base level data into users table."""
    table = _get_table(connection=connection, name="users")

    # Insert user into database
    username = "user_null_active"
    _insert_with_defaults(
        connection=connection,
        table=table,
        values={
            "username": username,
            "active": None,
            "type": "Researcher",
        },
    )

    return {"username": username}


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


@pytest.mark.parametrize(
    "target_revision, down_revision, setup_func, upgrade_assertion, downgrade_assertion",
    [
        (
            "a5a40d843415",
            "d117e6299dc9",
            _setup_projects,
            _assert_projects_after_upgrade,
            _assert_projects_after_downgrade,
        ),
        (
            "666003748d14",
            "a5a40d843415",
            _setup_user_with_null_active,
            _assert_user_active_after_upgrade,
            _assert_user_active_after_downgrade,
        ),
        (
            "0c9c237cced5",
            "eb395af90e18",
            _setup_unit_without_quota,
            _assert_unit_quota_after_upgrade,
            _assert_unit_quota_after_downgrade,
        ),
        (
            "0cd0a3b251e0",
            "3d610b382383",
            _setup_unit_without_contact_email,
            _assert_unit_contact_email_after_upgrade,
            _assert_unit_contact_email_after_downgrade,
        ),
    ],
)
def test_data_migrations_transform_existing_rows(
    migrated_database,  # fixture from conftest.py
    target_revision,
    down_revision,
    setup_func,
    upgrade_assertion,
    downgrade_assertion,
):
    """Ensure data migrations transform existing rows as expected.

    Every revision pair has it's own setup.

    Only revisions that actually rewrite existing rows are tested.
    Other revisions are already tested by upgrade and downgrade tests above.
    """

    # Build flask app bound to throwaway db
    app = create_app(testing=True, database_uri=migrated_database)

    # Build engine to talk to same throwaway db outside of flask session
    engine = create_engine(migrated_database)

    # Run tests
    try:
        # Run downgrade to specific revision
        _run_migration(app=app, migration_func=flask_migrate.downgrade, revision=down_revision)

        # Fill db with relevant data, e.g. projects, users, units etc.
        with engine.begin() as connection:
            context = setup_func(connection=connection)

        # Run upgrade to specific revision
        _run_migration(app=app, migration_func=flask_migrate.upgrade, revision=target_revision)

        # Verify that the upgrade worked as intended
        with engine.begin() as connection:
            upgrade_assertion(connection=connection, context=context)

        # Run downgrade to specific revision, again
        _run_migration(app=app, migration_func=flask_migrate.downgrade, revision=down_revision)

        # Verify that the downgrade worked as intended
        with engine.begin() as connection:
            downgrade_assertion(connection=connection, context=context)

        # Run upgrade to specific revision, again
        _run_migration(app=app, migration_func=flask_migrate.upgrade, revision=target_revision)
    finally:
        engine.dispose()
