"""Initialize Flask app."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import pytz
import logging

# Installed
import flask
import click
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from logging.config import dictConfig
from authlib.integrations import flask_client as auth_flask_client
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
import flask_mail
import flask_bootstrap
import flask_login
import flask_caching

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlalchemy

####################################################################################################
# GLOBAL VARIABLES ############################################################## GLOBAL VARIABLES #
####################################################################################################

# Current time zone
C_TZ = pytz.timezone("Europe/Stockholm")

# Database - not yet init
db = SQLAlchemy()

# Email setup - not yet init
mail = flask_mail.Mail()

# Marshmallows for parsing and validating
ma = Marshmallow()

# Authentication
oauth = auth_flask_client.OAuth()
basic_auth = HTTPBasicAuth()
auth = HTTPTokenAuth()

# Login - web routes
login_manager = flask_login.LoginManager()
login_manager.login_view = "auth_blueprint.login"

# Actions for logging
actions = {}

# Limiter
limiter = Limiter(key_func=get_remote_address)

# Caching
cache = flask_caching.Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_THRESHOLD": 1000})


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
    flask_bootstrap.Bootstrap(app)
    # Setup logging handlers
    setup_logging(app)

    # Adding limiter logging
    for handler in app.logger.handlers:
        limiter.logger.addHandler(handler)

    # Set app.logger as the general logger
    app.logger = logging.getLogger("general")
    app.logger.info("Logging initiated.")

    # Initialize database
    db.init_app(app)

    cache.init_app(app)

    # Initialize mail setup
    mail.init_app(app)

    # Avoid very extensive logging when sending emails
    app.extensions["mail"].debug = 0

    # Initialize marshmallows
    ma.init_app(app)

    # Errors, TODO: Move somewhere else?
    @app.errorhandler(sqlalchemy.exc.SQLAlchemyError)
    def handle_sqlalchemyerror(e):
        return f"SQLAlchemyError: {e}", 500  # TODO: Fix logging and a page

    # Initialize login manager
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(user_id)

    oauth.init_app(app)

    # Initialize limiter
    limiter._storage_uri = app.config.get("RATELIMIT_STORAGE_URL")
    limiter.init_app(app)

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
        from dds_web.web.user import auth_blueprint

        app.register_blueprint(api_blueprint, url_prefix="/api/v1")
        app.register_blueprint(auth_blueprint, url_prefix="")

        # Set-up the schedulers
        dds_web.utils.scheduler_wrapper()

        from dds_web.api.user import ENCRYPTION_KEY_CHAR_LENGTH

        if len(app.config.get("SECRET_KEY")) != ENCRYPTION_KEY_CHAR_LENGTH:
            from dds_web.api.errors import KeyLengthError

            raise KeyLengthError(ENCRYPTION_KEY_CHAR_LENGTH)

        return app


@click.command("init-dev-db")
@click.argument("dev_db_size", type=click.Choice(["small", "big"]))
@flask.cli.with_appcontext
def fill_db_wrapper(dev_db_size):
    flask.current_app.logger.info("Initializing development db")
    assert flask.current_app.config["USE_LOCAL_DB"]
    db.create_all()
    if dev_db_size == "small":
        from dds_web.development.db_init import fill_db

        fill_db()
    elif dev_db_size == "big":
        import dds_web.development.factories

        dds_web.development.factories.create_all()

    flask.current_app.logger.info("DB filled")
