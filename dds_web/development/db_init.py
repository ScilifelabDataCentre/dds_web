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
        public_id="public_unit_id",
        name="Unit 1",
        internal_ref="fac",
        safespring=current_app.config.get("DDS_SAFE_SPRING_PROJECT"),
    ),
    Unit(
        public_id="public_unit_id_2",
        name="Unit 2",
        internal_ref="fac2",
        safespring=current_app.config.get("DDS_SAFE_SPRING_PROJECT"),
    ),
]

# Create Projects
projects = [
    Project(
        public_id="public_project_id",
        title="test project_title",
        category="Category",
        date_created=dds_web.utils.timestamp(),
        date_updated=dds_web.utils.timestamp(),
        status="Ongoing",
        description="This is a test project. You will be able to upload to but NOT download "
        "from this project. Create a new project to test the entire system. ",
        pi="PI",
        size=7357,
        bucket=f"publicproj-{str(dds_web.utils.timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
        public_key="08D0D813DD7DD2541DF58A7E5AB651D20299F741732B0DC8B297A2D4CB43626C",
        private_key="5F39E1650CC7592EF2A06FDD37FB576EFE19C1C0C4FBDF0C799EBE19FD4B731805C25213D9398B09A7F3A0CCADA71B7E",
        privkey_salt="C2BB3FB2BBBA0DD01A6A2F5937C9D84C",
        privkey_nonce="D652B8C4554B675FB780A6EE",
        unit_id=units[0],
    ),
    Project(
        public_id="unused_project_id",
        title="unused project",
        category="Category",
        date_created=dds_web.utils.timestamp(),
        date_updated=dds_web.utils.timestamp(),
        status="Ongoing",
        description="This is a test project to check for permissions.",
        pi="PI",
        size=7357,
        bucket=f"unusedprojectid-{str(dds_web.utils.timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
        public_key="08D0D813DD7DD2541DF58A7E5AB651D20299F741732B0DC8B297A2D4CB43626C",
        private_key="5F39E1650CC7592EF2A06FDD37FB576EFE19C1C0C4FBDF0C799EBE19FD4B731805C25213D9398B09A7F3A0CCADA71B7E",
        privkey_salt="C2BB3FB2BBBA0DD01A6A2F5937C9D84C",
        privkey_nonce="D652B8C4554B675FB780A6EE",
        unit_id=units[1],
    ),
]

# Create Users
users = [
    User(
        username="username",
        password=auth.gen_argon2hash(password="password"),
        role="researcher",
        first_name="User",
        last_name="Name",
        unit_id=None,
    ),
    User(
        username="admin",
        password=auth.gen_argon2hash(password="password"),
        role="admin",
        first_name="Ad",
        last_name="Min",
        unit_id=None,
    ),
    User(
        username="unit_admin",
        password=auth.gen_argon2hash(password="password"),
        role="unit",
        first_name="Unit",
        last_name="Admin",
        unit_id=units[0],
    ),
    User(
        username="unit",
        password=auth.gen_argon2hash(password="password"),
        role="unit",
        first_name="Faci",
        last_name="Lity",
        unit_id=units[0],
    ),
]

# Create Files
files = [
    File(
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
        project_id=projects[0],
    )
]

# Create Versions
versions = [
    Version(
        size_stored=files[0].size_stored,
        time_uploaded=dds_web.utils.timestamp(),
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
