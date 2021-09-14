"""Initialize Flask app."""

# IMPORTS ########################################################### IMPORTS #

# Standard library
from datetime import datetime, timedelta
import pytz
import logging
import os
import pathlib
import time

# Installed
import flask
import click
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_marshmallow import Marshmallow
from logging.handlers import RotatingFileHandler
from logging.config import dictConfig
from authlib.integrations import flask_client as auth_flask_client

# Own modules

# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #

app_obj = flask.Flask(__name__, instance_relative_config=False)
db = SQLAlchemy()
ma = Marshmallow(app_obj)
C_TZ = pytz.timezone("Europe/Stockholm")
oauth = auth_flask_client.OAuth(app_obj)
actions = {"api_blueprint.auth": "User Authentication", "api_blueprint.proj_auth": "Project Access"}

# FUNCTIONS ####################################################### FUNCTIONS #


@app_obj.before_request
def prepare():
    # Test line for global
    flask.g.current_user = flask.session.get("current_user")
    flask.g.is_facility = flask.session.get("is_facility")
    flask.g.is_admin = flask.session.get("is_admin")
    if flask.g.is_facility:
        flask.g.facility_name = flask.session.get("facility_name")
        flask.g.facility_id = flask.session.get("facility_id")


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
                    "basedir": app_obj.config.get("LOGS_DIR"),
                    "formatter": "general",
                },
                "actions": {
                    "level": logging.INFO,
                    "class": "dds_web.dds_rotating_file_handler.DDSRotatingFileHandler",
                    "filename": "actions",
                    "basedir": app_obj.config.get("LOGS_DIR"),
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

    app_obj.config.from_envvar("DDS_APP_CONFIG", silent=True)

    # Setup logging handlers
    setup_logging()

    # Set app.logger as the general logger
    app_obj.logger = logging.getLogger("general")
    app_obj.logger.info("Logging initiated.")

    # Initialize database
    db.init_app(app_obj)

    app_obj.cli.add_command(fill_db_wrapper)

    # initialize OIDC
    oauth.register(
        "default_login",
        client_secret=app_obj.config.get("OIDC_CLIENT_SECRET"),
        client_id=app_obj.config.get("OIDC_CLIENT_ID"),
        server_metadata_url=app_obj.config.get("OIDC_ACCESS_TOKEN_URL"),
        client_kwargs={"scope": "openid profile email"},
    )
    app_obj.logger.info("Attaching blueprints.")
    with app_obj.app_context():  # Everything in here has access to sessions
        from dds_web import routes  # Import routes
        from dds_web.database import models

        from dds_web.api import api_blueprint

        app_obj.register_blueprint(api_blueprint, url_prefix="/api/v1")

        from dds_web.user import user_blueprint

        app_obj.register_blueprint(user_blueprint, url_prefix="/user")

        from dds_web.admin import admin_blueprint

        app_obj.register_blueprint(admin_blueprint, url_prefix="/admin")

        from dds_web.project import project_blueprint

        app_obj.register_blueprint(project_blueprint, url_prefix="/project")

        return app_obj


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


@click.command('init-dev-db')
@flask.cli.with_appcontext
def fill_db_wrapper():
    app_obj.logger.info("Initializing development db")
    assert app_obj.config["USE_LOCAL_DB"]
    db.create_all()
    from dds_web.development.db_init import fill_db
    fill_db()
    app_obj.logger.info("DB filled")
