import os
import uuid
import pytest
from sqlalchemy_utils import create_database, database_exists

from dds_web import create_app, db

mysql_root_password = os.getenv("MYSQL_ROOT_PASSWORD")
DATABASE_URI = "mysql+pymysql://root:{}@db/DeliverySystemTest".format(mysql_root_password)


def demo_data():
    from dds_web.database.models import Project, User, Unit
    from dds_web.security import auth
    from dds_web.utils import timestamp

    users = [
        User(
            username="username",
            unit_id=None,
            password=auth.gen_argon2hash(password="password"),
            role="researcher",
            name="User Name",
        ),
        User(
            username="admin",
            unit_id=None,
            password=auth.gen_argon2hash(password="password"),
            role="admin",
            name="Ad Min",
        ),
        User(
            username="admin2",
            unit_id=None,
            password=auth.gen_argon2hash(password="password"),
            role="admin",
            name="Ad Min2",
        ),
    ]

    units = [
        Unit(
            public_id="unit0",
            name="Unit 0",
            internal_ref="someunit",
            safespring="dds.example.com",
        ),
        Unit(
            public_id="unit1",
            name="Unit 1",
            internal_ref="anotherunit",
            safespring="dds.example.com",
        ),
    ]

    projects = [
        Project(
            public_id="public_project_id",
            title="test project_title",
            status="Ongoing",
            description="This is a test project. You will be able to upload to but NOT download "
            "from this project. Create a new project to test the entire system. ",
            pi="PI",
            size=7357,
            bucket=f"publicproj-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
            public_key="2E2F3F1C91ECA5D4CBEFFB59A487511319E76FBA34709C6CC49BF9DC0EC8B10B",
            private_key="494D26A977118F7E6AB6D87548E762DEB85C537292D65618FDC18A0EFAB6B860468F17BA26F7A0BDA4F23938A5A10801",
            privkey_salt="23D9FF66A5EE317D45D13809070C6D3F",
            privkey_nonce="847D75C4C548474FC54714AA",
        ),
        Project(
            public_id="unused_project_id",
            title="unused project",
            status="Ongoing",
            description="This is a test project to check for permissions.",
            pi="PI",
            size=7357,
            bucket=f"unusedprojectid-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
            public_key="2E2F3F1C91ECA5D4CBEFFB59A487511319E76FBA34709C6CC49BF9DC0EC8B10B",
            private_key="494D26A977118F7E6AB6D87548E762DEB85C537292D65618FDC18A0EFAB6B860468F17BA26F7A0BDA4F23938A5A10801",
            privkey_salt="23D9FF66A5EE317D45D13809070C6D3F",
            privkey_nonce="847D75C4C548474FC54714AA",
        ),
        Project(
            public_id="restricted_project_id",
            title="Elite project",
            status="Ongoing",
            description="This is a test project without user access for researchers and Admin2",
            pi="PI",
            size=7357,
            bucket=f"unusedprojectid-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
            public_key="2E2F3F1C91ECA5D4CBEFFB59A487511319E76FBA34709C6CC49BF9DC0EC8B10B",
            private_key="494D26A977118F7E6AB6D87548E762DEB85C537292D65618FDC18A0EFAB6B860468F17BA26F7A0BDA4F23938A5A10801",
            privkey_salt="23D9FF66A5EE317D45D13809070C6D3F",
            privkey_nonce="847D75C4C548474FC54714AA",
        ),
    ]

    return (users, units, projects)


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
            users, units, projects = demo_data()
            db.session.add_all(units)
            db.session.flush()
            users[1].unit = units[0]
            db.session.add_all(users)
            db.session.flush()
            db.session.add_all(projects)
            projects[0].unit = units[0]
            projects[1].unit = units[1]
            users[0].projects.append(projects[0])
            users[1].projects.append(projects[0])
            users[1].projects.append(projects[2])
            users[2].projects.append(projects[0])
            db.session.commit()

            try:
                yield client
            finally:
                db.session.rollback()
                # Removes all data from the database
                for table in reversed(db.metadata.sorted_tables):
                    db.session.execute(table.delete())
                db.session.commit()
