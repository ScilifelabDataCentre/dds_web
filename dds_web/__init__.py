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

# imports related to scheduling
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from utils import invoice_units, remove_invoiced, remove_expired

# Own modules

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


def create_app():
    """Construct the core application."""
    # Initiate app object
    app = flask.Flask(__name__, instance_relative_config=False)

    # Default development config
    app.config.from_object("dds_web.config.Config")

    # User config file, if e.g. using in production
    app.config.from_envvar("DDS_APP_CONFIG", silent=True)

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
        from dds_web.database import models

        # Need to import auth so that the modifications to the auth objects take place
        import dds_web.security.auth

        # Register blueprints
        from dds_web.api import api_blueprint

        app.register_blueprint(api_blueprint, url_prefix="/api/v1")

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

    ####################################################################################################
    # BACKGROUND SCHEDULER #############################################################################
    ####################################################################################################

    scheduler = BackgroundScheduler(
        {
            "apscheduler.jobstores.default": {
                "type": "sqlalchemy",
                # "url": flask.current_app.config.get("SQLALCHEMY_DATABASE_URI"),
                "engine": db.engine,
            },
            "apscheduler.timezone": "Europe/Stockholm",
        }
    )


scheduler.print_jobs()

# Schedule invoicing calculations every 30 days
# TODO (ina): Change to correct interval - 30 days
scheduler.add_job(
    invoice_units,
    "cron",
    id="calc_costs",
    replace_existing=True,
    month="1-12",
    day="1-31",
    hour="0",
)

# Schedule delete of rows in version table after a specific amount of time
# Currently: First of every month
scheduler.add_job(
    remove_invoiced,
    "cron",
    id="remove_versions",
    replace_existing=True,
    month="1-12",
    day="1",
    hour="1",
)

# Schedule move of rows in files table after a specific amount of time
# to DeletedFiles (does not exist yet) table
# Currently: First of every month
scheduler.add_job(
    remove_expired,
    "cron",
    id="remove_expired",
    replace_existing=True,
    month="1-12",
    day="1",
    hour="2",
)

# Schedule delete rows in expiredfiles table after a specific amount of time
# TODO (ina): Change interval - 1 day?
scheduler.add_job(
    permanent_delete,
    "cron",
    id="permanent_delete",
    replace_existing=True,
    month="1-12",
    day="1-31",
    hour="3",
)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())
