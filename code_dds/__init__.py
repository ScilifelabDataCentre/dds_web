"""Initialize Flask app."""

# IMPORTS ########################################################### IMPORTS #

# Standard library

# Installed
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

# Own modules


# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #

db = SQLAlchemy()


# FUNCTIONS ####################################################### FUNCTIONS #

def create_app():
    """Construct the core application."""

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.Config')

    db.init_app(app)    # Initialize database

    with app.app_context():     # Everything in here has access to sessions
        from code_dds import routes  # Import routes

        db.drop_all()       # Make sure it's the latest db
        db.create_all()     # Create database tables for our data models

        fill_db()           # Fill db with initial entries (for development)

        return app


def fill_db():
    """Fills the database with initial entries used for development."""

    from code_dds.models import User, Project, Facility, S3Project

    user1 = User(first_name="Ross", last_name="Geller", username="rossy",
                 password="rosspass",
                 settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
                 email="ross.geller@museum.com", phone="070-000 00 01",
                 admin=False)

    facility1 = Facility(name="National Seq Facility", internal_ref="nsf",
                         username="fac1_username", password="b93be04bfdcdace50c5f5d8e88a3e08e2d6fdd1258095735f5a395e9013d70ec",
                         settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
                         email="supprt@nsf.se", phone="08 000 00 00")

    project1 = Project(title="Whole Genome Sequencing", category="Genomics",
                       order_date=func.now(), delivery_date=None,
                       status="Ongoing", sensitive=True, description="test",
                       pi="", owner=user1, facility=facility1, size=0,
                       delivery_option="S3", public_key="8F88EAA7B72DB95BE36D6B1EA83064C3F5F8B5306ACB7457B1E49659FF60142C",
                       private_key="privatekey", nonce="nonce")

    s3proj1 = S3Project(id="s3proj1", project_id=project1)

    # Foreign key/relationship updates
    user1.user_projects.append(project1)
    facility1.fac_projects.append(project1)
    project1.project_s3.append(s3proj1)

    # Add user and facility, the rest is automatically added and commited
    db.session.add(user1)
    db.session.add(facility1)

    # Required for change in db
    db.session.commit()
