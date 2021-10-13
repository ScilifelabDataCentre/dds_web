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
from dds_web.database import models
import dds_web.utils

####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def fill_db():
    """Fills the database with initial entries used for development."""

    # Foreign key/relationship updates:
    # The model with the row db.relationship should append the row of the model with foreign key

    # Create first project - leave out foreign key
    project_1 = models.Project(
        public_id="project_1",
        title="First Project",
        status="status not implemented yet",
        description="This is a test project. You will be able to upload to but NOT download "
        "from this project. Create a new project to test the entire system. ",
        pi="PI Name",
        size=0,
        bucket=f"testbucket",
        public_key="669F9C66CDCB6C08165453617101FD04884D3D23367A5C088FD8DF2C5F30CA49",
        private_key="180245F63CE331516155851C08A919B79FEA62D69B3FC34033C678A64176657668D0D483E860540873C4EB5F58E2F074",
        privkey_salt="2AD29A881F9783021142905D6B5902C9",
        privkey_nonce="7758E89F838E76E5202E0D71",
    )

    # Create second project - leave out foreign key
    project_2 = models.Project(
        public_id="project_2",
        title="Second Project",
        status="status not implemented yet",
        description="This is a test project. You will be able to upload to but NOT download "
        "from this project. Create a new project to test the entire system. ",
        pi="PI Name",
        size=0,
        bucket=f"secondproject-{str(dds_web.utils.timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
        public_key="669F9C66CDCB6C08165453617101FD04884D3D23367A5C088FD8DF2C5F30CA49",
        private_key="180245F63CE331516155851C08A919B79FEA62D69B3FC34033C678A64176657668D0D483E860540873C4EB5F58E2F074",
        privkey_salt="2AD29A881F9783021142905D6B5902C9",
        privkey_nonce="7758E89F838E76E5202E0D71",
    )

    # Create first research user
    researchuser_1 = models.ResearchUser(
        username="researchuser_1",
        password=auth.gen_argon2hash(password="password"),
        name="First Research User",
    )
    # Create association with user - not owner of project
    project_1_user_1_association = models.ProjectUsers(owner=False)
    # Connect research user to association row. = (not append) due to one user per ass. row
    project_1_user_1_association.researchuser = researchuser_1
    # Connect research user to project. append (not =) due to many users per project
    project_1.researchusers.append(project_1_user_1_association)

    # Create second research user
    researchuser_2 = models.ResearchUser(
        username="researchuser_2",
        password=auth.gen_argon2hash(password="password"),
        name="Second Research User",
    )
    # Create association with user - is owner of project
    project_1_user_2_association = models.ProjectUsers(owner=True)
    # Connect research user to association row. = (not append) due to one user per ass. row
    project_1_user_2_association.researchuser = researchuser_2
    # Connect research user to project. append (not =) due to many users per project
    project_1.researchusers.append(project_1_user_2_association)

    # Create first unit user
    unituser_1 = models.UnitUser(
        username="unituser_1",
        password=auth.gen_argon2hash(password="password"),
        name="First Unit User",
    )
    # Create second unit user
    unituser_2 = models.UnitUser(
        username="unituser_2",
        password=auth.gen_argon2hash(password="password"),
        name="Second Unit User",
    )

    # Add created project
    unituser_1.created_projects.append(project_1)
    unituser_2.created_projects.append(project_2)

    # Create first unit
    unit_1 = models.Unit(
        public_id="unit_1",
        name="Unit 1",
        internal_ref="someunit",
        safespring=current_app.config.get("DDS_SAFE_SPRING_PROJECT"),
    )
    # Connect project to unit. append (not =) due to many projects per unit
    unit_1.projects.extend([project_1, project_2])
    unit_1.users.extend([unituser_1, unituser_2])

    # Add unit to database - relationship will add the rest because of foreign key constraints
    db.session.add(unit_1)

    db.session.commit()
