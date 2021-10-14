import os
import uuid
import pytest
from sqlalchemy_utils import create_database, database_exists
from dds_web.database.models import ResearchUser, UnitUser, SuperAdmin, Unit, Project, ProjectUsers

from dds_web import create_app, db

mysql_root_password = os.getenv("MYSQL_ROOT_PASSWORD")
DATABASE_URI = "mysql+pymysql://root:{}@db/DeliverySystemTest".format(mysql_root_password)


def demo_data():
    from dds_web.security import auth
    from dds_web.utils import timestamp

    units = [
        Unit(
            name="Unit 1",
            public_id=os.urandom(16).hex(),
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
        ResearchUser(
            username="projectowner",
            password=auth.gen_argon2hash(password="password"),
            name="Project Owner",
        ),
        UnitUser(
            username="unituser",
            password=auth.gen_argon2hash(password="password"),
            name="Unit User",
            is_admin=False,
        ),
        UnitUser(
            username="unituser2",
            password=auth.gen_argon2hash(password="password"),
            name="Unit User 2",
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
            bucket=f"eliteprojectid-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
            public_key="2E2F3F1C91ECA5D4CBEFFB59A487511319E76FBA34709C6CC49BF9DC0EC8B10B",
            private_key="494D26A977118F7E6AB6D87548E762DEB85C537292D65618FDC18A0EFAB6B860468F17BA26F7A0BDA4F23938A5A10801",
            privkey_salt="23D9FF66A5EE317D45D13809070C6D3F",
            privkey_nonce="847D75C4C548474FC54714AA",
        ),
    ]

    return (units, users, projects)


@pytest.fixture
def client():
    # Create database specific for tests
    if not database_exists(DATABASE_URI):
        create_database(DATABASE_URI)
    app = create_app(testing=True, database_uri=DATABASE_URI)
    with app.test_client() as client:
        with app.app_context():

            db.create_all()
            units, users, projects = demo_data()
            # Create association with user - not owner of project
            project_1_user_1_association = ProjectUsers(owner=False)
            # Connect research user to association row. = (not append) due to one user per ass. row
            project_1_user_1_association.researchuser = users[0]
            # Connect research user to project. append (not =) due to many users per project
            projects[0].researchusers.append(project_1_user_1_association)

            # Create association with user - is owner of project
            project_1_user_2_association = ProjectUsers(owner=True)
            # Connect research user to association row. = (not append) due to one user per ass. row
            project_1_user_2_association.researchuser = users[1]
            # Connect research user to project. append (not =) due to many users per project
            projects[0].researchusers.append(project_1_user_2_association)

            # Add created project
            users[2].created_projects.append(projects[0])
            users[3].created_projects.append(projects[1])

            units[0].projects.extend([projects[0], projects[1]])
            units[0].users.extend([users[2], users[3]])

            db.session.add(units[0])
            # db.session.add_all(users)
            # db.session.add_all(projects)
            db.session.commit()

            try:
                yield client
            finally:
                db.session.rollback()
                # Removes all data from the database
                for table in reversed(db.metadata.sorted_tables):
                    db.session.execute(table.delete())
                db.session.commit()
