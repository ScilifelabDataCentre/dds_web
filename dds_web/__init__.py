"""Initialize Flask app."""

# IMPORTS ########################################################### IMPORTS #

# Standard library
from datetime import datetime, timedelta
import pytz
import logging

# Installed
from flask import Flask, g, session
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from logging.config import dictConfig
from authlib.integrations import flask_client as auth_flask_client
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth

# Own modules

# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #

app = Flask(__name__, instance_relative_config=False)
db = SQLAlchemy()
ma = Marshmallow(app)
C_TZ = pytz.timezone("Europe/Stockholm")
oauth = auth_flask_client.OAuth(app)
actions = {"api_blueprint.auth": "User Authentication", "api_blueprint.proj_auth": "Project Access"}
basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()
auth = MultiAuth(basic_auth, token_auth)

# FUNCTIONS ####################################################### FUNCTIONS #


@app.before_request
def prepare():
    # Test line for global
    g.current_user = session.get("current_user")
    # g.current_user_id = session.get("current_user_id")
    g.is_facility = session.get("is_facility")
    g.is_admin = session.get("is_admin")
    if g.is_facility:
        g.facility_name = session.get("facility_name")
        g.facility_id = session.get("facility_id")


def setup_logging():
    """Setup loggers"""

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "general": {"format": "[%(asctime)s] %(module)s [%(levelname)s] %(message)s"},
                "actions": {
                    "format": "[%(asctime)s] [%(levelname)s] <%(module)s> :: [%(result)s | Attempted : %(action)s | Project : %(project)s | User : %(current_user)s]"
                },
            },
            "handlers": {
                "general": {
                    "level": logging.DEBUG,
                    "class": "dds_web.dds_rotating_file_handler.DDSRotatingFileHandler",
                    "filename": "dds",
                    "basedir": app.config.get("LOGS_DIR"),
                    "formatter": "general",
                },
                "actions": {
                    "level": logging.INFO,
                    "class": "dds_web.dds_rotating_file_handler.DDSRotatingFileHandler",
                    "filename": "actions",
                    "basedir": app.config.get("LOGS_DIR"),
                    "formatter": "actions",
                },
                "console": {
                    "level": logging.DEBUG,
                    "class": "logging.StreamHandler",
                    "formatter": "general",
                },
            },
            "loggers": {
                "general": {
                    "handlers": ["general", "console"],
                    "level": logging.DEBUG,
                    "propagate": False,
                },
                "actions": {"handlers": ["actions"], "level": logging.INFO, "propagate": False},
            },
        }
    )


def create_app():
    """Construct the core application."""

    # Default development config
    app.config.from_object("dds_web.config.Config")

    # User config file, if e.g. using in production
    app.config.from_envvar("DDS_APP_CONFIG", silent=True)

    # Setup logging handlers
    setup_logging()

    # Set app.logger as the general logger
    app.logger = logging.getLogger("general")
    app.logger.info("Logging initiated.")

    # Initialize database
    db.init_app(app)

    # initialize OIDC
    oauth.register(
        "default_login",
        client_secret=app.config.get("OIDC_CLIENT_SECRET"),
        client_id=app.config.get("OIDC_CLIENT_ID"),
        server_metadata_url=app.config.get("OIDC_ACCESS_TOKEN_URL"),
        client_kwargs={"scope": "openid profile email"},
    )
    with app.app_context():  # Everything in here has access to sessions
        from dds_web import routes  # Import routes
        from dds_web.database import models

        # db.drop_all()       # Make sure it's the latest db
        db.create_all()  # Create database tables for our data models

        # puts in test info for local DB, will be removed later
        if app.config["USE_LOCAL_DB"]:
            try:
                from dds_web.development.db_init import fill_db

                fill_db()
            except Exception as err:
                # Look into why, but this will be removed soon anyway
                app.logger.exception(str(err))

        from dds_web.api import api_blueprint

        app.register_blueprint(api_blueprint, url_prefix="/api/v1")

        from dds_web.user import user_blueprint

        app.register_blueprint(user_blueprint, url_prefix="/user")

        from dds_web.admin import admin_blueprint

        app.register_blueprint(admin_blueprint, url_prefix="/admin")

        from dds_web.project import project_blueprint

        app.register_blueprint(project_blueprint, url_prefix="/project")

        return app


def timestamp(dts=None, datetime_string=None, ts_format="%Y-%m-%d %H:%M:%S.%f%z"):
    """Gets the current time. Formats timestamp.

    Returns:
        str:    Timestamp in format 'YY-MM-DD_HH-MM-SS'

    """

    if datetime_string is not None:
        datetime_stamp = datetime.strptime(datetime_string, ts_format)
        return str(datetime_stamp.date())

    now = datetime.now(tz=C_TZ) if dts is None else dts
    t_s = str(now.strftime(ts_format))
    return t_s


def token_expiration(valid_time: int = 48):
    now = datetime.now(tz=C_TZ)
    expire = now + timedelta(hours=valid_time)

    return timestamp(dts=expire)
