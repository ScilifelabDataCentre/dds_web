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
from flask import Flask, g, render_template, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_marshmallow import Marshmallow
from logging.handlers import RotatingFileHandler
from logging.config import dictConfig
from authlib.integrations import flask_client as auth_flask_client

# Own modules

# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #

app = Flask(__name__, instance_relative_config=False)
db = SQLAlchemy()
ma = Marshmallow(app)
C_TZ = pytz.timezone("Europe/Stockholm")
oauth = auth_flask_client.OAuth(app)

# CLASSES ########################################################### CLASSES #


class DDSRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def __init__(
        self,
        filename,
        basedir,
        mode="a",
        maxBytes=1e9,
        backupCount=0,
        encoding=None,
        delay=0,
    ):
        """
        Custom RotatingFileHandler, logs to the file `<basedir>/<filename>.log`
        and renames the current file to `<basedir>/<filename>_[timestamp].log` when the file size
        reaches <maxBytes> --> Current logging always to <filename>.log.
        """

        self.today_ = datetime.now() if not hasattr(self, "today_") else self.today_
        self.basedir_ = pathlib.Path(basedir)  # Log directory
        self.basename = pathlib.Path(filename)  # Base for all filenames
        self.active_file_name = self.basedir_ / self.basename.with_suffix(".log")  # Active file

        # Initiate super class
        logging.handlers.RotatingFileHandler.__init__(
            self, self.active_file_name, mode, maxBytes, backupCount, encoding, delay
        )

    def shouldRollover(self, record):
        """
        Checks if the FileHandler should do a rollover of the log file.
        """

        if self.stream is None:
            self.stream = self._open()

        # Check if the file is at max size
        if self.maxBytes > 0:
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, 2)
            if self.stream.tell() + len(msg) >= self.maxBytes:
                # Create time stamp and rename the current log file to contain rollover timestamp
                new_today = datetime.now()
                replacement_name = pathlib.Path(
                    str(self.basename)
                    + "_"
                    + self.today_.strftime("%Y-%m-%d-%H-%M-%S")
                    + "_"
                    + new_today.strftime("%Y-%m-%d-%H-%M-%S")
                    + ".log"
                )
                self.active_file_name.rename(target=pathlib.Path(self.basedir_ / replacement_name))
                self.today_ = new_today
                return 1

        return 0


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


def create_app():
    """Construct the core application."""

    # Defaults
    app.config.from_object("dds_web.config.Config")

    # User config file, if using in production
    app.config.from_envvar("DDS_APP_CONFIG", silent=True)

    # Setup logging handlers
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "general": {"format": "[%(asctime)s] %(module)s [%(levelname)s] %(message)s"},
                "actions": {
                    "format": "[%(asctime)s] [%(levelname)s] %(module)s - [User: %(current_user)s] [Action: %(action)s] [%(message)s]"
                },
            },
            "handlers": {
                "general": {
                    "level": logging.DEBUG,
                    "class": "dds_web.DDSRotatingFileHandler",
                    "filename": "dds",
                    "basedir": app.config.get("LOG_DIR"),
                    "formatter": "general",
                },
                "actions": {
                    "level": logging.INFO,
                    "class": "dds_web.DDSRotatingFileHandler",
                    "filename": "actions",
                    "basedir": app.config.get("LOG_DIR"),
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

    # Set app.logger as the general logger
    app.logger = logging.getLogger("general")
    app.logger.info("Logging initiated.")

    # action_logger = logging.getLogger("actions")
    # action_logger.info("Logging initiated.", extra={"action": "initiation", "current_user": "root", })

    db.init_app(app)  # Initialize database
    # ma.init_app(app)

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
                # don't care why, this will be removed soon anyway
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
