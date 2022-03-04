# Standard Library
import os
import unittest.mock
import datetime
import subprocess
import uuid

# Installed
import flask_migrate
import pytest
from sqlalchemy_utils import create_database, database_exists, drop_database
import boto3

# Own
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
    File,
    Version,
    Identifier,
    DeletionRequest,
)
import dds_web.utils
from dds_web import create_app, db
from dds_web.security.project_user_keys import (
    generate_project_key_pair,
    share_project_private_key,
)
from dds_web.security.tokens import encrypted_jwt_token

mysql_root_password = os.getenv("MYSQL_ROOT_PASSWORD")
DATABASE_URI_BASE = f"mysql+pymysql://root:{mysql_root_password}@db/DeliverySystemTestBase"
DATABASE_URI = f"mysql+pymysql://root:{mysql_root_password}@db/DeliverySystemTest"


def fill_basic_db(db):
    """
    Fill the database with basic data.
    """

    units, users, projects = add_data_to_db()
    db.session.add_all(units)
    db.session.add_all(users)

    db.session.commit()

    generate_project_key_pair(users[2], units[0].projects[0])
    generate_project_key_pair(users[2], units[0].projects[2])
    generate_project_key_pair(users[2], units[0].projects[4])

    generate_project_key_pair(users[3], units[0].projects[1])
    generate_project_key_pair(users[3], units[0].projects[3])

    db.session.commit()

    user2_token = encrypted_jwt_token(
        username=users[2].username,
        sensitive_content="password",
    )
    share_project_private_key(
        from_user=users[2],
        to_another=users[0],
        from_user_token=user2_token,
        project=projects[0],
    )
    share_project_private_key(
        from_user=users[2],
        to_another=users[1],
        from_user_token=user2_token,
        project=projects[0],
    )

    user3_token = encrypted_jwt_token(
        username=users[3].username,
        sensitive_content="password",
    )
    share_project_private_key(
        from_user=users[3],
        to_another=users[6],
        from_user_token=user3_token,
        project=projects[3],
    )

    db.session.commit()


def new_test_db(uri):
    dbname = uri[uri.rindex("/") + 1 :]
    dbname_base = DATABASE_URI_BASE[DATABASE_URI_BASE.rindex("/") + 1 :]
    dump_args = ["mysqldump", "-h", "db", "-u", "root", f"-p{mysql_root_password}", dbname_base]
    load_args = ["mysql", "-h", "db", "-u", "root", f"-p{mysql_root_password}", dbname]
    proc1 = subprocess.run(dump_args, capture_output=True)
    proc1 = subprocess.run(dump_args, stdout=subprocess.PIPE)
    proc2 = subprocess.run(load_args, input=proc1.stdout, capture_output=True)


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
        ),
        Unit(
            name="The league of the extinct gentlemen",
            public_id=os.urandom(16).hex(),
            external_display_name="Retraction guaranteed",
            contact_email="tloteg@mailtrap.io",
            internal_ref="Unit to test user deletion",
            safespring_endpoint="endpoint",
            safespring_name="dds.example.com",
            safespring_access="access",
            safespring_secret="secret",
        ),
    ]

    users = [
        ResearchUser(
            username="researchuser",
            password="password",
            name="Research User",
        ),
        ResearchUser(
            username="projectowner",
            password="password",
            name="Project Owner",
        ),
        UnitUser(
            username="unituser",
            password="password",
            name="Unit User",
            is_admin=False,
        ),
        UnitUser(
            username="unituser2",
            password="password",
            name="Unit User 2",
            is_admin=False,
        ),
        UnitUser(
            username="unitadmin",
            password="password",
            name="Unit Admin",
            is_admin=True,
        ),
        SuperAdmin(
            username="superadmin",
            password="password",
            name="Super Admin",
        ),
        ResearchUser(
            username="researchuser2",
            password="password",
            name="Research User 2",
        ),
        ResearchUser(
            username="delete_me_researcher",
            password="password",
            name="Research User to test deletions",
        ),
        UnitUser(
            username="delete_me_unituser",
            password="password",
            name="Unit User to test deletions",
            is_admin=False,
        ),
        UnitUser(
            username="delete_me_unitadmin",
            password="password",
            name="Unit Admin to test deletions",
            is_admin=True,
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
        ),
        Project(
            public_id="unused_project_id",
            title="unused project",
            description="This is a test project to check for permissions.",
            pi="PI",
            bucket=f"unusedprojectid-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
        ),
        Project(
            public_id="restricted_project_id",
            title="Elite project",
            description="This is a test project without user access for the current research users",
            pi="PI",
            bucket=f"eliteprojectid-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
        ),
        Project(
            public_id="second_public_project_id",
            title="second project",
            description="This is a second test project. You will be able to upload to but NOT download ",
            pi="PI",
            bucket=f"secondpublicproj-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
        ),
        Project(
            public_id="file_testing_project",
            title="file testing project",
            description="this project is used for testing to add new files.",
            pi="file testing project PI",
            bucket="bucket",
        ),
    ]

    files_and_versions = [
        (
            File(
                name="filename1",
                name_in_bucket="name_in_bucket_1",
                subpath="filename1/subpath",
                size_original=15000,
                size_stored=10000,
                compressed=True,
                salt="A" * 32,
                public_key="B" * 64,
                checksum="C" * 64,
            ),
            [
                Version(
                    size_stored=10000,
                    time_uploaded=dds_web.utils.current_time(),
                ),
                Version(
                    size_stored=30000,
                    time_uploaded=dds_web.utils.current_time() - datetime.timedelta(days=1),
                ),
            ],
        ),
        (
            File(
                name="filename2",
                name_in_bucket=str(uuid.uuid4()),
                subpath="filename2/subpath",
                size_original=15000,
                size_stored=10000,
                compressed=True,
                salt="D" * 32,
                public_key="E" * 64,
                checksum="F" * 64,
            ),
            [
                Version(
                    size_stored=10000,
                    time_uploaded=dds_web.utils.current_time(),
                )
            ],
        ),
    ]

    for i in range(5):
        files_and_versions.append(
            (
                File(
                    name=f"filename_a{i+1}",
                    name_in_bucket=str(uuid.uuid4()),
                    subpath=f"sub/path/to/folder{i+1}",
                    size_original=5000 * (i + 1),
                    size_stored=3000 * (i + 1),
                    compressed=True,
                    salt=chr(ord("A") + 3 * i) * 32,
                    public_key=chr(ord("B") + 3 * i) * 64,
                    checksum=chr(ord("C") + 3 * i) * 64,
                ),
                [
                    Version(
                        size_stored=3000 * (j + 1),
                        time_uploaded=dds_web.utils.current_time() - datetime.timedelta(days=j),
                    )
                    for j in range(i + 1)
                ],
            ),
        )

    for i in range(5):
        files_and_versions.append(
            (
                File(
                    name=f"filename_b{i+1}",
                    name_in_bucket=str(uuid.uuid4()),
                    subpath=f"sub/path/to/files",
                    size_original=500 * (i + 1),
                    size_stored=300 * (i + 1),
                    compressed=True,
                    salt=chr(ord("Z") - 3 * i) * 32,
                    public_key=chr(ord("Y") - 3 * i) * 64,
                    checksum=chr(ord("X") - 3 * i) * 64,
                ),
                [
                    Version(
                        size_stored=300 * (j + 1),
                        time_uploaded=dds_web.utils.current_time() - datetime.timedelta(days=j),
                    )
                    for j in range(i + 1)
                ],
            ),
        )

    invites = [Invite(**{"email": "existing_invite_email@mailtrap.io", "role": "Researcher"})]

    return (units, users, projects, invites, files_and_versions)


def add_data_to_db():
    units, users, projects, invites, files_and_versions = demo_data()
    for project in projects:
        project.project_statuses.append(
            ProjectStatuses(
                **{"status": "In Progress", "date_created": dds_web.utils.current_time()}
            )
        )
    # Create association with files for project 0:
    for file, versions in files_and_versions:
        projects[0].files.append(file)
        for version in versions:
            file.versions.append(version)
            projects[0].file_versions.append(version)

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
    users[0].identifiers.append(Identifier(username="researchuser", identifier="A" * 58))
    users[0].deletion_request.append(
        DeletionRequest(
            requester_id="researchuser",
            email="researchuser@mailtrap.io",
            issued=dds_web.utils.current_time(),
        )
    )

    add_email_to_user_6 = Email(
        user_id="researchuser2", email="researchuser2@mailtrap.io", primary=True
    )
    users[6].emails.append(add_email_to_user_6)

    users[1].emails.append(
        Email(user_id="projectowner", email="projectowner@mailtrap.io", primary=True)
    )
    users[2].emails.append(Email(user_id="unituser", email="unituser1@mailtrap.io", primary=True))
    users[2].identifiers.append(Identifier(username="unituser", identifier="B" * 58))
    users[2].deletion_request.append(
        DeletionRequest(
            requester_id="unituser",
            email="unituser1@mailtrap.io",
            issued=dds_web.utils.current_time(),
        )
    )

    users[3].emails.append(Email(user_id="unituser2", email="unituser2@mailtrap.io", primary=True))
    users[4].emails.append(Email(user_id="unitadmin", email="unitadmin@mailtrap.io", primary=True))
    users[5].emails.append(
        Email(user_id="superadmin", email="superadmin@mailtrap.io", primary=True)
    )
    users[5].identifiers.append(Identifier(username="superadmin", identifier="C" * 58))

    users[7].emails.append(
        Email(
            user_id="delete_me_researcher", email="delete_me_researcher@mailtrap.io", primary=True
        )
    )
    users[8].emails.append(
        Email(user_id="delete_me_unituser", email="delete_me_unituser@mailtrap.io", primary=True)
    )
    users[9].emails.append(
        Email(user_id="delete_me_unitadmin", email="delete_me_unitadmin@mailtrap.io", primary=True)
    )

    # Add created project
    users[2].created_projects.append(projects[0])
    users[3].created_projects.append(projects[1])
    users[2].created_projects.append(projects[2])
    users[3].created_projects.append(projects[3])
    users[2].created_projects.append(projects[4])

    units[0].projects.extend(projects)
    units[0].users.extend([users[2], users[3], users[4]])
    units[0].invites.append(invites[0])

    units[1].users.extend([users[8], users[9]])

    for user in users:
        user.active = True

    return units, users, projects


@pytest.fixture(scope="session")
def setup_database():
    # Create database specific for tests
    if not database_exists(DATABASE_URI_BASE):
        create_database(DATABASE_URI_BASE)
        app = create_app(testing=True, database_uri=DATABASE_URI_BASE)
        with app.test_request_context():
            with app.test_client():
                flask_migrate.upgrade()
                fill_basic_db(db)
                db.engine.dispose()

    if not database_exists(DATABASE_URI):
        create_database(DATABASE_URI)
    try:
        yield None
    finally:
        # Drop database to save container space
        if not os.environ.get("SAVE_DB", False):
            drop_database(DATABASE_URI)
            drop_database(DATABASE_URI_BASE)


@pytest.fixture(scope="function")
def client(setup_database):
    # Fill database with values from base db
    new_test_db(DATABASE_URI)

    app = create_app(testing=True, database_uri=DATABASE_URI)
    with app.test_request_context():
        with app.test_client() as client:
            try:
                yield client
            finally:
                # aborts any pending transactions
                db.session.rollback()
                # Removes all data from the database
                for table in reversed(db.metadata.sorted_tables):
                    db.session.execute(table.delete())
                db.session.commit()
                db.engine.dispose()


@pytest.fixture(scope="module")
def module_client(setup_database):
    # Fill database with values from base db
    new_test_db(DATABASE_URI)

    app = create_app(testing=True, database_uri=DATABASE_URI)
    with app.test_request_context():
        with app.test_client() as client:
            try:
                yield client
            finally:
                # aborts any pending transactions
                db.session.rollback()
                # Removes all data from the database
                for table in reversed(db.metadata.sorted_tables):
                    db.session.execute(table.delete())
                db.session.commit()
                db.engine.dispose()


@pytest.fixture()
def boto3_session():
    """Create a mock boto3 session since no access permissions are in place for testing"""
    with unittest.mock.patch.object(boto3.session.Session, "resource") as mock_session:
        yield mock_session
