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
from dds_web.database import models
from dds_web.security.project_user_keys import (
    generate_project_key_pair,
    share_project_private_key,
)
from dds_web.security.tokens import encrypted_jwt_token
import dds_web.utils

####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def fill_db():
    """Fills the database with initial entries used for development."""

    # Foreign key/relationship updates:
    # The model with the row db.relationship should append the row of the model with foreign key

    password = "password"

    # Super Admin
    superadmin = models.SuperAdmin(username="superadmin", password=password, name="Super Admin")
    superadmin_email = models.Email(email="superadmin@mailtrap.io", primary=True)
    superadmin_email.user = superadmin
    db.session.add(superadmin_email)

    # Create first unit user
    unituser_1 = models.UnitUser(
        username="unituser_1",
        password=password,
        name="First Unit User",
        active=True,
    )

    # Create second unit user
    unituser_2 = models.UnitUser(
        username="unituser_2",
        password=password,
        name="Second Unit User",
        active=True,
    )

    unitadmin_1 = models.UnitUser(
        username="unitadmin_1", password=password, name="Unit Admin 1", active=True, is_admin=True
    )
    unitadmin_2 = models.UnitUser(
        username="unitadmin_2", password=password, name="Unit Admin 2", active=True, is_admin=True
    )
    unitadmin_3 = models.UnitUser(
        username="unitadmin_3", password=password, name="Unit Admin 3", active=True, is_admin=True
    )

    # create a few e-mail addresses
    email_unituser_1 = models.Email(email="unituser1@mailtrap.io", primary=True)
    email_unituser_1b = models.Email(email="unituser1@somewhereelse.se", primary=False)
    email_unituser_2 = models.Email(email="unituser2@mailtrap.io", primary=True)
    email_unitadmin_1 = models.Email(email="unitadmin1@mailtrap.io", primary=True)
    email_unitadmin_2 = models.Email(email="unitadmin2@mailtrap.io", primary=True)
    email_unitadmin_3 = models.Email(email="unitadmin3@mailtrap.io", primary=True)

    email_unituser_1.user = unituser_1
    email_unituser_1b.user = unituser_1
    email_unituser_2.user = unituser_2
    email_unitadmin_1.user = unitadmin_1
    email_unitadmin_2.user = unitadmin_2
    email_unitadmin_3.user = unitadmin_3

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

    unit_1.users.extend([unituser_1, unituser_2, unitadmin_1, unitadmin_2, unitadmin_3])

    # Create first project - leave out foreign key
    project_1 = models.Project(
        public_id="project_1",
        title="First Project",
        description="This is a test project. You will be able to upload to but NOT download "
        "from this project. Create a new project to test the entire system. ",
        pi="support@example.com",
        bucket="testbucket",
    )

    project_1.project_statuses.append(
        models.ProjectStatuses(
            **{"status": "In Progress", "date_created": dds_web.utils.current_time()}
        )
    )

    unituser_1.created_projects.append(project_1)

    generate_project_key_pair(unituser_1, project_1)

    # Create second project - leave out foreign key
    project_2 = models.Project(
        public_id="project_2",
        title="Second Project",
        description="This is a test project. You will be able to upload to but NOT download "
        "from this project. Create a new project to test the entire system. ",
        pi="support@example.com",
        bucket=f"secondproject-{str(dds_web.utils.timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
    )

    project_2.project_statuses.append(
        models.ProjectStatuses(
            **{"status": "In Progress", "date_created": dds_web.utils.current_time()}
        )
    )

    unituser_2.created_projects.append(project_2)

    generate_project_key_pair(unituser_2, project_2)

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
    email_researchuser_1.user = researchuser_1
    # Create association with user - not owner of project
    project_1_user_1_association = models.ProjectUsers(owner=False)
    # Connect research user to association row. = (not append) due to one user per ass. row
    project_1_user_1_association.researchuser = researchuser_1
    # Connect project to association row. = (not append) due to one project per ass. row
    project_1_user_1_association.project = project_1

    researchuser_1.active = True

    email_researchuser_2 = models.Email(email="researchuser2@mailtrap.io", primary=True)
    # Create second research user
    researchuser_2 = models.ResearchUser(
        username="researchuser_2",
        password=password,
        name="Second Research User",
    )
    email_researchuser_2.user = researchuser_2
    # Create association with user - is owner of project
    project_1_user_2_association = models.ProjectUsers(owner=True)
    # Connect research user to association row. = (not append) due to one user per ass. row
    project_1_user_2_association.researchuser = researchuser_2
    # Connect project to association row. = (not append) due to one project per ass. row
    project_1_user_2_association.project = project_1

    researchuser_2.active = True

    # Add unit to database - relationship will add the rest because of foreign key constraints
    db.session.add(unit_1)

    db.session.commit()

    unituser_1_token = encrypted_jwt_token(
        username=unituser_1.username,
        sensitive_content=password,
    )

    share_project_private_key(
        from_user=unituser_1,
        to_another=researchuser_1,
        from_user_token=unituser_1_token,
        project=project_1,
    )

    share_project_private_key(
        from_user=unituser_1,
        to_another=researchuser_2,
        from_user_token=unituser_1_token,
        project=project_1,
    )

    db.session.commit()
