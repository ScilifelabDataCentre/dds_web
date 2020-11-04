"""USED ONLY DURING DEVELOPMENT! Adds test data to the database."""

from code_dds.models import User, Project, Facility, S3Project, File, Tokens
from code_dds import db
from sqlalchemy import func
import os


def fill_db():
    """Fills the database with initial entries used for development."""

    user1 = User(first_name="FirstName", last_name="LastName",
                 username="username1",
                 password=("9f247257e7d0ef00ad5eeeda7740233167d36b265a918536b8"
                           "c27a8efd774bc5"),
                 settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
                 email="user@email.com", phone="070-000 00 01",
                 admin=False)

    facility1 = Facility(name="Facility1", internal_ref="fac1",
                         username="fac1_username",
                         password=("b93be04bfdcdace50c5f5d8e88a3e08e2d6fdd1258"
                                   "095735f5a395e9013d70ec"),
                         settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
                         email="supprt@fac.se", phone="08 000 00 00")

    project1 = Project(title="Project1", category="Category1",
                       order_date=func.now(), delivery_date=None,
                       status="Ongoing", sensitive=True, description="test",
                       pi="", owner=user1, facility=facility1, size=0,
                       size_enc=0, delivery_option="S3",
                       public_key=("304F3C52DBD6E502DC3BE1EAB361605D2D00077592"
                                   "2ECE9AA5875933FACA6157"),
                       private_key=(
                           "B72DD6FCA04E22D0D47D8F8E5A943EC3564D6F1AE"
                           "A493E30A0B25F0B83B947A45BC5D55AB67B393B5A"
                           "2543E3A6C4F1725C9AF3C8163004CFA3046A1019F8"
                       ),
                       salt="026937046F41A071ECE8F438CF9CC1CB",
                       nonce="B917F9CEA1254CC82F0A7EFE")

    s3proj1 = S3Project(id="s3proj1", project_id=project1)

    token = Tokens(token=os.urandom(16).hex(), project_id=project1)

    # Foreign key/relationship updates
    user1.user_projects.append(project1)
    facility1.fac_projects.append(project1)
    project1.project_s3.append(s3proj1)
    # project1.project_files.append(file1)
    project1.project_tokens.append(token)

    # Add user and facility, the rest is automatically added and commited
    db.session.add(user1)
    db.session.add(facility1)
    # db.session.add(file1)

    # Required for change in db
    db.session.commit()
