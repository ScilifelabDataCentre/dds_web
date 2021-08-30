"""USED ONLY DURING DEVELOPMENT! Adds test data to the database."""

import os
import uuid

from flask import current_app

from dds_web import db, timestamp
from dds_web.crypt import auth

from dds_web.database.models import User, Project, Facility, File, Version, Email


def fill_db():
    """Fills the database with initial entries used for development."""

    facilities = [
        Facility(
            public_id="public_facility_id",
            name="Facility 1",
            internal_ref="fac",
            safespring=current_app.config.get("DDS_SAFE_SPRING_PROJECT"),
        ),
        Facility(
            public_id="public_facility_id_2",
            name="Facility 2",
            internal_ref="fac2",
            safespring=current_app.config.get("DDS_SAFE_SPRING_PROJECT"),
        ),
    ]

    projects = [
        Project(
            public_id="public_project_id",
            title="test project_title",
            category="Category",
            date_created=timestamp(),
            date_updated=timestamp(),
            status="Ongoing",
            description="This is a test project. You will be able to upload to but NOT download "
            "from this project. Create a new project to test the entire system. ",
            pi="PI",
            size=7357,
            bucket=f"publicproj-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
            public_key="08D0D813DD7DD2541DF58A7E5AB651D20299F741732B0DC8B297A2D4CB43626C",
            private_key="5F39E1650CC7592EF2A06FDD37FB576EFE19C1C0C4FBDF0C799EBE19FD4B731805C25213D9398B09A7F3A0CCADA71B7E",
            privkey_salt="C2BB3FB2BBBA0DD01A6A2F5937C9D84C",
            privkey_nonce="D652B8C4554B675FB780A6EE",
            facility_id=facilities[0],
        ),
        Project(
            public_id="unused_project_id",
            title="unused project",
            category="Category",
            date_created=timestamp(),
            date_updated=timestamp(),
            status="Ongoing",
            description="This is a test project to check for permissions.",
            pi="PI",
            size=7357,
            bucket=f"unusedprojectid-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
            public_key="08D0D813DD7DD2541DF58A7E5AB651D20299F741732B0DC8B297A2D4CB43626C",
            private_key="5F39E1650CC7592EF2A06FDD37FB576EFE19C1C0C4FBDF0C799EBE19FD4B731805C25213D9398B09A7F3A0CCADA71B7E",
            privkey_salt="C2BB3FB2BBBA0DD01A6A2F5937C9D84C",
            privkey_nonce="D652B8C4554B675FB780A6EE",
            facility_id=facilities[1],
        ),
    ]

    users = [
        User(
            username="username",
            password=auth.gen_argon2hash(password="password"),
            role="researcher",
            permissions="-gl--",
            first_name="User",
            last_name="Name",
            facility_id=None,
        ),
        User(
            username="admin",
            password=auth.gen_argon2hash(password="password"),
            role="admin",
            permissions="a-l--",
            first_name="Ad",
            last_name="Min",
            facility_id=None,
        ),
        User(
            username="facility_admin",
            password=auth.gen_argon2hash(password="password"),
            role="facility",
            permissions="a-l--",
            first_name="Facility",
            last_name="Admin",
            facility_id=facilities[0],
        ),
        User(
            username="facility",
            password=auth.gen_argon2hash(password="password"),
            role="facility",
            permissions="--lpr",
            first_name="Faci",
            last_name="Lity",
            facility_id=facilities[0],
        ),
    ]

    files = [
        File(
            public_id="file_public_id",
            name="notafile.txt",
            name_in_bucket="testtesttest.txt",
            subpath="subpath",
            size_original=0,  # bytes
            size_stored=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            project_id=projects[0],
        )
    ]

    versions = [
        Version(
            size_stored=files[0].size_stored,
            time_uploaded=timestamp(),
            active_file=files[0],
            project_id=projects[0],
        )
    ]

    emails = [
        Email(user=users[0], email="one@email.com", primary=True),
        Email(user=users[0], email="two@email.com", primary=False),
        Email(user=users[1], email="three@email.com", primary=True),
        Email(user=users[1], email="four@email.com", primary=False),
    ]

    # Foreign key/relationship updates
    try:
        for p in projects:
            if p.public_id != "unused_project_id":
                for u in users:
                    u.projects.append(p)
    except Exception:
        raise

    try:
        for e in emails[0:2]:
            users[0].emails.append(e)
    except Exception:
        raise

    try:
        for e in emails[2:4]:
            users[1].emails.append(e)
    except Exception:
        raise

    try:
        for u in users:
            if u.facility_id:
                facilities[0].users.append(u)
    except Exception:
        raise

    try:
        for f in files:
            projects[0].files.append(f)
    except Exception:
        raise

    try:
        for p in projects:
            facilities[0].projects.append(p)
    except Exception:
        raise

    try:

        for v in versions:
            projects[0].file_versions.append(v)
            files[0].versions.append(v)
    except Exception:
        raise

    # As long as we add the facilities, the rest will be filled due to foreign key constraints etc
    # NOTE: This results in integrityerror on restart!
    try:
        db.session.add_all(facilities)
    except Exception:
        raise

    # Required for change in db
    try:
        db.session.commit()
    except Exception:
        raise
