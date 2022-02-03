"""USED ONLY DURING DEVELOPMENT! Adds test data to the database."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import uuid
import os

# Installed
from flask import current_app

# Own modules
from dds_web import db
from dds_web.security import project_keys
from dds_web.database import models
import dds_web.utils

####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def fill_db():
    """Fills the database with initial entries used for development."""

    # Foreign key/relationship updates:
    # The model with the row db.relationship should append the row of the model with foreign key

    password = "password"

    # Create first unit user
    unituser_1 = models.UnitUser(
        username="unituser_1",
        password=password,
        name="First Unit User",
    )
    dds_web.cache.set(unituser_1.username, password)
    unituser_1.kd_salt = os.urandom(32)

    # Create second unit user
    unituser_2 = models.UnitUser(
        username="unituser_2",
        password=password,
        name="Second Unit User",
    )
    dds_web.cache.set(unituser_2.username, password)
    unituser_2.kd_salt = os.urandom(32)

    # Create first unit
    unit_1 = models.Unit(
        public_id="unit_1",
        name="Unit 1",
        external_display_name="Unit 1 external",
        contact_email="support@example.com",
        internal_ref="someunit",
        safespring_endpoint=current_app.config.get("SAFESPRING_URL"),
        safespring_name=current_app.config.get("DDS_SAFESPRING_PROJECT"),
        safespring_access=current_app.config.get("DDS_SAFESPRING_ACCESS"),
        safespring_secret=current_app.config.get("DDS_SAFESPRING_SECRET"),
    )

    unit_1.users.extend([unituser_1, unituser_2])

    project_1_unituser_1_key_dict = project_keys.generate_project_key_pair(unituser_1)

    # Create first project - leave out foreign key
    project_1 = models.Project(
        public_id="project_1",
        title="First Project",
        description="This is a test project. You will be able to upload to but NOT download "
        "from this project. Create a new project to test the entire system. ",
        pi="PI Name",
        bucket=f"testbucket",
        public_key=project_1_unituser_1_key_dict["public_key"],
    )

    project_1_unituser_1_project_keys = models.ProjectKeys(
        project_id=project_1.id,
        user_id=unituser_1.username,
        key=project_1_unituser_1_key_dict["encrypted_private_key"]["encrypted_key"],
        nonce=project_1_unituser_1_key_dict["encrypted_private_key"]["nonce"],
    )

    project_1.project_statuses.append(
        models.ProjectStatuses(
            **{"status": "In Progress", "date_created": dds_web.utils.current_time()}
        )
    )

    unituser_1.created_projects.append(project_1)

    # GIVE UNITUSER 2 ACCESS TO PROJECT 1

    project_2_unituser_2_key_dict = project_keys.generate_project_key_pair(unituser_2)

    # Create second project - leave out foreign key
    project_2 = models.Project(
        public_id="project_2",
        title="Second Project",
        description="This is a test project. You will be able to upload to but NOT download "
        "from this project. Create a new project to test the entire system. ",
        pi="PI Name",
        bucket=f"secondproject-{str(dds_web.utils.timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
        public_key=project_2_unituser_2_key_dict["public_key"],
    )

    project_2_unituser_2_project_keys = models.ProjectKeys(
        project_id=project_2.id,
        user_id=unituser_1.username,
        key=project_2_unituser_2_key_dict["encrypted_private_key"]["encrypted_key"],
        nonce=project_2_unituser_2_key_dict["encrypted_private_key"]["nonce"],
    )

    project_2.project_statuses.append(
        models.ProjectStatuses(
            **{"status": "In Progress", "date_created": dds_web.utils.current_time()}
        )
    )

    unituser_2.created_projects.append(project_2)

    # GIVE UNITUSER 1 ACCESS TO PROJECT 2

    # Connect project to unit. append (not =) due to many projects per unit
    unit_1.projects.extend([project_1, project_2])

    # Create an email
    email_researchuser_1 = models.Email(email="researchuser1@mailtrap.io", primary=True)
    # Create first research user
    researchuser_1 = models.ResearchUser(
        username="researchuser_1",
        password=password,
        name="First Research User",
    )
    dds_web.cache.set(researchuser_1.username, password)
    researchuser_1.kd_salt = os.urandom(32)
    email_researchuser_1.user = researchuser_1
    # Create association with user - not owner of project
    project_1_user_1_association = models.ProjectUsers(owner=False)
    # Connect research user to association row. = (not append) due to one user per ass. row
    project_1_user_1_association.researchuser = researchuser_1
    # Connect project to association row. = (not append) due to one project per ass. row
    project_1_user_1_association.project = project_1

    # GIVE RESEARCHUSER 1 ACCESS TO PROJECT 1

    # Create second research user
    researchuser_2 = models.ResearchUser(
        username="researchuser_2",
        password=password,
        name="Second Research User",
    )
    dds_web.cache.set(researchuser_2.username, password)
    researchuser_2.kd_salt = os.urandom(32)
    # Create association with user - is owner of project
    project_1_user_2_association = models.ProjectUsers(owner=True)
    # Connect research user to association row. = (not append) due to one user per ass. row
    project_1_user_2_association.researchuser = researchuser_2
    # Connect project to association row. = (not append) due to one project per ass. row
    project_1_user_2_association.project = project_1

    # GIVE RESEARCHUSER 2 ACCESS TO PROJECT 1

    # Add unit to database - relationship will add the rest because of foreign key constraints
    db.session.add(unit_1)

    db.session.commit()
