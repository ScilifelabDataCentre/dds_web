import os
import pytest
from sqlalchemy_utils import create_database, database_exists

from dds_web import create_app, db

mysql_root_password = os.getenv("MYSQL_ROOT_PASSWORD")
DATABASE_URI = "mysql+pymysql://root:{}@db/DeliverySystemTest".format(mysql_root_password)


def demo_data():
    from dds_web.database.models import User
    from dds_web.security import auth

    users = [
        User(
            username="username",
            password=auth.gen_argon2hash(password="password"),
            role="researcher",
            first_name="User",
            last_name="Name",
            unit_id=None,
        )
    ]

    return users


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
            users = demo_data()
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
