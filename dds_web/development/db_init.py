"""USED ONLY DURING DEVELOPMENT! Adds test data to the database."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import uuid

# Installed
from flask import current_app

# Own modules
from dds_web import db
from dds_web.security import auth
from dds_web.database.models import User, Project, Unit, File, Version, Email
import dds_web.utils

####################################################################################################
# ITEMS #################################################################################### ITEMS #
####################################################################################################

# Create Units
units = [
    Unit(
        public_id="unit1",
        name="Unit 1",
        internal_ref="someunit",
        safespring=current_app.config.get("DDS_SAFE_SPRING_PROJECT"),
    ),
    Unit(
        public_id="unit2",
        name="Unit 2",
        internal_ref="anotherunit",
        safespring=current_app.config.get("DDS_SAFE_SPRING_PROJECT"),
    ),
]

# Create Projects
projects = [
    Project(
        public_id="public_project_id",
        title="test project_title",
        status="Ongoing",
        description="This is a test project. You will be able to upload to but NOT download "
        "from this project. Create a new project to test the entire system. ",
        pi="PI",
        size=7357,
        bucket=f"publicproj-{str(dds_web.utils.timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
        public_key="2E2F3F1C91ECA5D4CBEFFB59A487511319E76FBA34709C6CC49BF9DC0EC8B10B",
        private_key="494D26A977118F7E6AB6D87548E762DEB85C537292D65618FDC18A0EFAB6B860468F17BA26F7A0BDA4F23938A5A10801",
        privkey_salt="23D9FF66A5EE317D45D13809070C6D3F",
        privkey_nonce="847D75C4C548474FC54714AA",
        unit_id=units[0],
    ),
    Project(
        public_id="unused_project_id",
        title="unused project",
        status="Ongoing",
        description="This is a test project to check for permissions.",
        pi="PI",
        size=7357,
        bucket=f"unusedprojectid-{str(dds_web.utils.timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
        public_key="2E2F3F1C91ECA5D4CBEFFB59A487511319E76FBA34709C6CC49BF9DC0EC8B10B",
        private_key="494D26A977118F7E6AB6D87548E762DEB85C537292D65618FDC18A0EFAB6B860468F17BA26F7A0BDA4F23938A5A10801",
        privkey_salt="23D9FF66A5EE317D45D13809070C6D3F",
        privkey_nonce="847D75C4C548474FC54714AA",
        unit_id=units[1],
    ),
]

# Create Users
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
        unit_id=units[0],
        password=auth.gen_argon2hash(password="password"),
        role="admin",
        name="Ad Min",
    ),
    User(
        username="unit_admin",
        unit_id=units[0],
        password=auth.gen_argon2hash(password="password"),
        role="unit",
        name="Unit Admin",
    ),
    User(
        username="unit",
        unit_id=units[0],
        password=auth.gen_argon2hash(password="password"),
        role="unit",
        name="Unit",
    ),
]


files = [
    File(
        project_id=projects[0],
        public_id="file_public_id",
        name="notafile.txt",
        name_in_bucket="testtesttest.txt",
        subpath=".",
        size_original=0,  # bytes
        size_stored=0,
        compressed=False,
        public_key="test",
        salt="test",
        checksum="",
    )
]

# Create Versions
versions = [
    Version(
        size_stored=files[0].size_stored,
        active_file=files[0],
        project_id=projects[0],
    )
]

# Create Emails
emails = [
    Email(user=users[0], email="one@email.com", primary=True),
    Email(user=users[0], email="two@email.com", primary=False),
    Email(user=users[1], email="three@email.com", primary=True),
    Email(user=users[1], email="four@email.com", primary=False),
]

# Add table rows to dict for development purposes
# Format:
# {
#     <name of table>: {
#         "table": <model>,
#         "rows": <rows created in code above>,
#         "unique": <name of unique column in table>
#     }
# }
development_rows = {
    "units": {
        "table": Unit,
        "rows": units,
        "unique": "public_id",
    },
    "projects": {
        "table": Project,
        "rows": projects,
        "unique": "public_id",
    },
    "users": {
        "table": User,
        "rows": users,
        "unique": "username",
    },
    "files": {
        "table": File,
        "rows": files,
        "unique": "public_id",
    },
    "versions": {
        "table": Version,
        "rows": versions,
        "unique": None,
    },
    "emails": {
        "table": Email,
        "rows": emails,
        "unique": "email",
    },
}

####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def check_if_fill(table, rows, unique) -> bool:
    """Check if the test entries are in the database."""

    # If there is no unique column in the table, it doesn't matter if the exact row exists
    if not unique:
        return True

    # Check those rows with public_id as unique column
    if unique == "public_id":
        for row in rows:
            retrieved_row = db.session.query(table.id).filter_by(public_id=row.public_id).first()
    # Check the rows with username as unique column
    if unique == "username":
        for row in rows:
            retrieved_row = (
                db.session.query(table.username).filter_by(username=row.username).first()
            )

    # Check the rows with email as unique column
    if unique == "email":
        for row in rows:
            retrieved_row = db.session.query(table.id).filter_by(email=row.email).first()

    return retrieved_row is None


def fill_db():
    """Fills the database with initial entries used for development."""

    # Don't fill db with development rows if they already exist -- will result in integrityerror
    for table, info in development_rows.items():
        if not check_if_fill(
            table=info.get("table"), rows=info.get("rows"), unique=info.get("unique")
        ):
            return

    # Foreign key/relationship updates:
    # The model with the row db.relationship should append the row of the model with foreign key

    # Add all projects to all user projects (for now, development)
    for p in projects:
        if p.public_id != "unused_project_id":
            for u in users:
                u.projects.append(p)

    # Add the first two email rows to the first user emails
    # and the last two email rows to the second user
    for e in emails[0:2]:
        users[0].emails.append(e)
    for e in emails[2:4]:
        users[1].emails.append(e)

    # Add the user accounts which are units to the first unit
    for u in users:
        if u.unit_id:
            units[0].users.append(u)

    # Add all files to the first project
    for f in files:
        projects[0].files.append(f)

    # Add all projects to the first unit
    for p in projects:
        units[0].projects.append(p)

    # Add all file versions to the first project and the first file
    # NOTE (ina): Is this required? Perhaps remove project versions and just have project -> file -> version
    for v in versions:
        projects[0].file_versions.append(v)
        files[0].versions.append(v)

    # As long as we add the units, the rest will be filled due to foreign key constraints etc
    # NOTE: This results in integrityerror on restart!
    db.session.add_all(units)

    # Required for change in db
    try:
        db.session.commit()
    except Exception:
        raise
