"""USED ONLY DURING DEVELOPMENT! Adds test data to the database."""

from code_dds.models import User, Project, Facility, File, Tokens
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

    project1 = Project(id="ff27977db6f5334dd055eefad2248d61", title="Project1",
                       category="Category1",
                       order_date=func.now(), delivery_date=None,
                       status="Ongoing", sensitive=True, description="test",
                       pi="", owner=user1, facility=facility1, size=0,
                       size_enc=0, delivery_option="S3",
                       public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
                       "7EFECAB889829253136B33"),
                       private_key=(
                           "83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
                           "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
                           "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
                           "A1BE27E07B9694061DADBD2B581E0AB0D8"
    ),
        salt="9A2694986A488E438DA998E73E93E9C4",
        nonce="D55240DB506C2C22CF248F18")

    # s3proj1 = S3Project(id="s3proj1", project_id=project1)

    token = Tokens(token=os.urandom(16).hex(), project_id=project1)

    # Foreign key/relationship updates
    user1.user_projects.append(project1)
    facility1.fac_projects.append(project1)
    # project1.project_s3.append(s3proj1)
    # project1.project_files.append(file1)
    project1.project_tokens.append(token)

    # Add user and facility, the rest is automatically added and commited
    db.session.add(user1)
    db.session.add(facility1)
    # db.session.add(file1)

    # Required for change in db
    db.session.commit()
