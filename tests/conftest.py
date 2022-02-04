# Standard Library
import os
import uuid
import unittest.mock

# Installed
import pytest
from sqlalchemy_utils import create_database, database_exists
import boto3

# Own
import dds_web.utils
from dds_web.database.models import (
    ResearchUser,
    UnitUser,
    SuperAdmin,
    Unit,
    Project,
    ProjectUsers,
    Invite,
    Email,
    ProjectStatuses,
)
from dds_web import create_app, db


mysql_root_password = os.getenv("MYSQL_ROOT_PASSWORD")
DATABASE_URI = "mysql+pymysql://root:{}@db/DeliverySystemTest".format(mysql_root_password)


def demo_data():
    from dds_web.utils import timestamp

    units = [
        Unit(
            name="Unit 1",
            public_id=os.urandom(16).hex(),
            external_display_name="Display Name",
            contact_email="support@example.com",
            internal_ref="someunit",
            safespring_endpoint="endpoint",
            safespring_name="dds.example.com",
            safespring_access="access",
            safespring_secret="secret",
        )
    ]

    users = [
        ResearchUser(
            username="researchuser",
            password="password",
            name="Research User",
            kd_salt=os.urandom(32),
        ),
        ResearchUser(
            username="projectowner",
            password="password",
            name="Project Owner",
            kd_salt=os.urandom(32),
        ),
        UnitUser(
            username="unituser",
            password="password",
            name="Unit User",
            is_admin=False,
            kd_salt=os.urandom(32),
        ),
        UnitUser(
            username="unituser2",
            password="password",
            name="Unit User 2",
            is_admin=False,
            kd_salt=os.urandom(32),
        ),
        UnitUser(
            username="unitadmin",
            password="password",
            name="Unit Admin",
            is_admin=True,
            kd_salt=os.urandom(32),
        ),
        SuperAdmin(
            username="superadmin",
            password="password",
            name="Super Admin",
            kd_salt=os.urandom(32),
        ),
        ResearchUser(
            username="researchuser2",
            password="password",
            name="Research User 2",
            kd_salt=os.urandom(32),
        ),
    ]

    projects = [
        Project(
            public_id="public_project_id",
            title="test project_title",
            description="This is a test project. You will be able to upload to but NOT download "
            "from this project. Create a new project to test the entire system. ",
            pi="PI",
            bucket=f"publicproj-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
            public_key="2E2F3F1C91ECA5D4CBEFFB59A487511319E76FBA34709C6CC49BF9DC0EC8B10B",
        ),
        Project(
            public_id="unused_project_id",
            title="unused project",
            description="This is a test project to check for permissions.",
            pi="PI",
            bucket=f"unusedprojectid-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
            public_key="2E2F3F1C91ECA5D4CBEFFB59A487511319E76FBA34709C6CC49BF9DC0EC8B10B",
        ),
        Project(
            public_id="restricted_project_id",
            title="Elite project",
            description="This is a test project without user access for the current research users",
            pi="PI",
            bucket=f"eliteprojectid-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
            public_key="2E2F3F1C91ECA5D4CBEFFB59A487511319E76FBA34709C6CC49BF9DC0EC8B10B",
        ),
        Project(
            public_id="second_public_project_id",
            title="second project",
            description="This is a second test project. You will be able to upload to but NOT download ",
            pi="PI",
            bucket=f"secondpublicproj-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
            public_key="2E2F3F1C91ECA5D4CBEFFB59A487511319E76FBA34709C6CC49BF9DC0EC8B10B",
        ),
        Project(
            public_id="file_testing_project",
            title="file testing project",
            description="this project is used for testing to add new files.",
            pi="file testing project PI",
            bucket="bucket",
            public_key="public_key",
        ),
    ]

    invites = [Invite(email="existing_invite_email@mailtrap.io", role="Researcher")]

    return (units, users, projects, invites)


def add_data_to_db():
    units, users, projects, invites = demo_data()
    for project in projects:
        project.project_statuses.append(
            ProjectStatuses(
                **{"status": "In Progress", "date_created": dds_web.utils.current_time()}
            )
        )
    # Create association with user - not owner of project
    project_0_user_0_association = ProjectUsers(owner=False)
    # Connect research user to association row. = (not append) due to one user per ass. row
    project_0_user_0_association.researchuser = users[0]
    # Connect research user to project. append (not =) due to many users per project
    projects[0].researchusers.append(project_0_user_0_association)

    # Create association with user - is owner of project
    project_0_user_1_association = ProjectUsers(owner=True)
    # Connect research user to association row. = (not append) due to one user per ass. row
    project_0_user_1_association.researchuser = users[1]
    # Connect research user to project. append (not =) due to many users per project
    projects[0].researchusers.append(project_0_user_1_association)

    # Create association with user - is owner of project
    project_3_user_6_association = ProjectUsers(owner=True)
    # Connect research user to association row. = (not append) due to one user per ass. row
    project_3_user_6_association.researchuser = users[6]
    # Connect research user to project. append (not =) due to many users per project
    projects[3].researchusers.append(project_3_user_6_association)

    add_email_to_user_0 = Email(
        user_id="researchuser", email="researchuser@mailtrap.io", primary=True
    )
    users[0].emails.append(add_email_to_user_0)

    add_email_to_user_6 = Email(
        user_id="researchuser2", email="researchuser2@mailtrap.io", primary=True
    )
    users[6].emails.append(add_email_to_user_6)
    # Add created project
    users[2].created_projects.append(projects[0])
    users[3].created_projects.append(projects[1])
    users[2].created_projects.append(projects[2])
    users[3].created_projects.append(projects[3])
    users[2].created_projects.append(projects[4])

    units[0].projects.extend(projects)
    units[0].users.extend([users[2], users[3], users[4]])
    units[0].invites.append(invites[0])

    return units[0]


@pytest.fixture(scope="function")
def client():
    # Create database specific for tests
    if not database_exists(DATABASE_URI):
        create_database(DATABASE_URI)
    app = create_app(testing=True, database_uri=DATABASE_URI)
    with app.test_client() as client:
        with app.app_context():

            db.create_all()

            unit = add_data_to_db()

            db.session.add(unit)
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


@pytest.fixture(scope="module")
def module_client():
    # Create database specific for tests
    if not database_exists(DATABASE_URI):
        create_database(DATABASE_URI)
    app = create_app(testing=True, database_uri=DATABASE_URI)
    with app.test_client() as client:
        with app.app_context():

            db.create_all()

            unit = add_data_to_db()

            db.session.add(unit)
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


@pytest.fixture()
def boto3_session():
    """Create a mock boto3 session since no access permissions are in place for testing"""
    with unittest.mock.patch.object(boto3.session.Session, "resource") as mock_session:
        yield mock_session
