"""Initialize Flask app."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
from datetime import datetime, timedelta
import pytz
import logging

# Installed
import flask
import click
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from logging.config import dictConfig
from authlib.integrations import flask_client as auth_flask_client
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth

# Own modules

####################################################################################################
# GLOBAL VARIABLES ############################################################## GLOBAL VARIABLES #
####################################################################################################

# Current time zone
C_TZ = pytz.timezone("Europe/Stockholm")

# Initiate app object
app_obj = flask.Flask(__name__, instance_relative_config=False)

# Database - not yet init
db = SQLAlchemy()

# Marshmallows for parsing and validating
ma = Marshmallow(app_obj)

# Authentication
oauth = auth_flask_client.OAuth(app_obj)
basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()
auth = MultiAuth(basic_auth, token_auth)

# Actions for logging
actions = {"api_blueprint.auth": "User Authentication", "api_blueprint.proj_auth": "Project Access"}


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

    # Default development config
    app_obj.config.from_object("dds_web.config.Config")

    # User config file, if e.g. using in production
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
    with app_obj.app_context():  # Everything in here has access to sessions
        from dds_web.database import models

        from dds_web.api import api_blueprint

        app_obj.register_blueprint(api_blueprint, url_prefix="/api/v1")

        return app_obj


@click.command("init-dev-db")
@flask.cli.with_appcontext
def fill_db_wrapper():
    app_obj.logger.info("Initializing development db")
    assert app_obj.config["USE_LOCAL_DB"]
    db.create_all()
    from dds_web.development.db_init import fill_db

    fill_db()
    app_obj.logger.info("DB filled")
