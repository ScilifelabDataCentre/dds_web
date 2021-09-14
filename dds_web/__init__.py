"""Initialize Flask app."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
from datetime import datetime, timedelta
import logging
import pytz
import time

# Installed
from flask import Flask, g, session
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from logging.config import dictConfig
from authlib.integrations import flask_client as auth_flask_client
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth
import flask_mail

# Own modules

####################################################################################################
# GLOBAL VARIABLES ############################################################## GLOBAL VARIABLES #
####################################################################################################

# Current time zone
C_TZ = pytz.timezone("Europe/Stockholm")

# Initiate app
app = Flask(__name__, instance_relative_config=False)

# Database - not yet init
db = SQLAlchemy()

# Email setup - not yet init
mail = flask_mail.Mail()

# Marshmallows for parsing and validating
ma = Marshmallow(app)

# Authentication
oauth = auth_flask_client.OAuth(app)
basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()
auth = MultiAuth(basic_auth, token_auth)

# Actions for logging
actions = {
    "api_blueprint.auth": "User Authentication",
    "api_blueprint.proj_auth": "Project Access",
    "api_blueprint.register_user": "Register New User",
}


####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def setup_logging():
    """Setup loggers"""

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "general": {"format": "[%(asctime)s] %(module)s [%(levelname)s] %(message)s"},
                "actions": {
                    "format": (
                        "[%(asctime)s] [%(levelname)s] <%(module)s> :: [%(result)s | "
                        "Attempted : %(action)s | Project : %(project)s | User : %(current_user)s]"
                    )
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
    mail.init_app(app)

    # FIXME
    # initialize OIDC
    # oauth.register(
    #     "default_login",
    #     client_secret=app.config.get("OIDC_CLIENT_SECRET"),
    #     client_id=app.config.get("OIDC_CLIENT_ID"),
    #     server_metadata_url=app.config.get("OIDC_ACCESS_TOKEN_URL"),
    #     client_kwargs={"scope": "openid profile email"},
    # )

    with app.app_context():  # Everything in here has access to sessions
        from dds_web.database import models

        db.create_all()  # Create database tables for our data models

        # puts in test info for local DB, will be removed later
        if app.config.get("USE_LOCAL_DB"):
            try:
                # Circular import if not imported here
                from dds_web.development import db_init

                db_init.fill_db()
            except Exception as err:
                # Look into why, but this will be removed soon anyway
                app.logger.exception(str(err))

        from dds_web.api import api_blueprint

        # Active REST API
        app.register_blueprint(api_blueprint, url_prefix="/api/v1")

        return app
