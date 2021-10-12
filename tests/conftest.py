import os
import pytest
from sqlalchemy_utils import create_database, database_exists

from dds_web import create_app, db

mysql_root_password = os.getenv("MYSQL_ROOT_PASSWORD")
DATABASE_URI = "mysql+pymysql://root:{}@db/DeliverySystemTest".format(mysql_root_password)


def demo_data():
    from dds_web.database.models import ResearchUser, UnitUser, SuperAdmin, Unit
    from dds_web.security import auth

    units = [
        Unit(
            name="Unit 1",
            internal_ref="someunit",
            safespring="dds.example.com",
        )
    ]

    users = [
        ResearchUser(
            username="researchuser",
            password=auth.gen_argon2hash(password="password"),
            name="Research User",
        ),
        UnitUser(
            username="unituser",
            password=auth.gen_argon2hash(password="password"),
            name="Unit User",
            is_admin=False,
        ),
        UnitUser(
            username="unitadmin",
            password=auth.gen_argon2hash(password="password"),
            name="Unit Admin",
            is_admin=True,
        ),
        SuperAdmin(
            username="superadmin",
            password=auth.gen_argon2hash(password="password"),
            name="Super Admin",
        ),
    ]

    return (users, units)


@pytest.fixture
def client():
    # Create database specific for tests
    if not database_exists(DATABASE_URI):
        create_database(DATABASE_URI)
    app = create_app(testing=True, database_uri=DATABASE_URI)
    with app.test_client() as client:
        with app.app_context():
            # Create all tables
            db.create_all()
            users, units = demo_data()
            # db.session.add_all(units)
            db.session.flush()
            users[1].unit = units[0]
            users[2].unit = units[0]
            db.session.add_all(users)
            db.session.commit()

            try:
                yield client
            finally:
                db.session.rollback()
                # Removes all data from the database
                for table in reversed(db.metadata.sorted_tables):
                    db.session.execute(table.delete())
                db.session.commit()
