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

####################################################################################################
# GLOBAL VARIABLES ############################################################## GLOBAL VARIABLES #
####################################################################################################

# Current time zone
C_TZ = pytz.timezone("Europe/Stockholm")

# Database - not yet init
db = SQLAlchemy()

# Marshmallows for parsing and validating
ma = Marshmallow()

# Authentication
oauth = auth_flask_client.OAuth()
basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()
auth = MultiAuth(basic_auth, token_auth)

# Actions for logging
actions = {"api_blueprint.auth": "User Authentication", "api_blueprint.proj_auth": "Project Access"}


####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def setup_logging(app):
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


def create_app(testing=False, database_uri=None):
    """Construct the core application."""
    # Initiate app object
    app = flask.Flask(__name__, instance_relative_config=False)

    # Default development config
    app.config.from_object("dds_web.config.Config")

    # User config file, if e.g. using in production
    app.config.from_envvar("DDS_APP_CONFIG", silent=True)

    # Test related configs
    if database_uri is not None:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    # Disables error catching during request handling
    app.config["TESTING"] = testing

    # Setup logging handlers
    setup_logging(app)

    # Set app.logger as the general logger
    app.logger = logging.getLogger("general")
    app.logger.info("Logging initiated.")

    # Initialize database
    db.init_app(app)

    ma.init_app(app)

    oauth.init_app(app)

    # initialize OIDC
    oauth.register(
        "default_login",
        client_secret=app.config.get("OIDC_CLIENT_SECRET"),
        client_id=app.config.get("OIDC_CLIENT_ID"),
        server_metadata_url=app.config.get("OIDC_ACCESS_TOKEN_URL"),
        client_kwargs={"scope": "openid profile email"},
    )

    app.cli.add_command(fill_db_wrapper)

    with app.app_context():  # Everything in here has access to sessions
        db.create_all()  # TODO: remove this when we have migrations
        from dds_web.database import models

        # Need to import auth so that the modifications to the auth objects take place
        import dds_web.security.auth

        # Register blueprints
        from dds_web.api import api_blueprint

        app.register_blueprint(api_blueprint, url_prefix="/api/v1")

        # Set-up the schedulers
        dds_web.utils.scheduler_wrapper()

        return app


@click.command("init-dev-db")
@flask.cli.with_appcontext
def fill_db_wrapper():
    flask.current_app.logger.info("Initializing development db")
    assert flask.current_app.config["USE_LOCAL_DB"]
    db.create_all()
    from dds_web.development.db_init import fill_db

    fill_db()
    flask.current_app.logger.info("DB filled")
