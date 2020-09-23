# "Web app template based on Flask and Sqlite3. With user account handling."

# import re

# __version__ = "0.0.2"


# class Constants:
#     VERSION = __version__
#     SOURCE_NAME = ""
#     SOURCE_URL = ""

#     BOOTSTRAP_VERSION = "4.3.1"
#     JQUERY_VERSION = "3.3.1"
#     DATATABLES_VERSION = "1.10.18"

#     NAME_RX = re.compile(r"^[a-z][a-z0-9_-]*$", re.I)
#     IUID_RX = re.compile(r"^[a-f0-9]{32,32}$", re.I)
#     EMAIL_RX = re.compile(r"^[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+$")

#     # User roles
#     ADMIN = "admin"
#     USER = "user"
#     USER_ROLES = (ADMIN, USER)

#     # User statuses
#     PENDING = "pending"
#     ENABLED = "enabled"
#     DISABLED = "disabled"
#     USER_STATUSES = [PENDING, ENABLED, DISABLED]

#     # Content types
#     HTML_MIMETYPE = "text/html"
#     JSON_MIMETYPE = "application/json"

#     # Misc
#     JSON_SCHEMA_URL = "http://json-schema.org/draft-07/schema#"

#     def __setattr__(self, key, value):
#         raise ValueError("cannot set constant")


# constants = Constants()

"""Initialize Flask app."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    """Construct the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.Config')

    db.init_app(app)

    with app.app_context():
        from . import routes  # Import routes
        db.create_all()  # Create database tables for our data models

        return app
