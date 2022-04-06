"""Initialize Flask app."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import logging
import datetime
import pathlib
import sys

# Installed
import click
import flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from logging.config import dictConfig
from authlib.integrations import flask_client as auth_flask_client
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
import flask_mail
import flask_login
import flask_migrate
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

# import flask_qrcode
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlalchemy
import structlog
import werkzeug

from dds_web.scheduled_tasks import scheduler


####################################################################################################
# GLOBAL VARIABLES ############################################################## GLOBAL VARIABLES #
####################################################################################################

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
login_manager.session_protection = "strong"

# Actions for logging
actions = {}

# Limiter
limiter = Limiter(key_func=get_remote_address)

# Migration
migrate = flask_migrate.Migrate()


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
                "default": {"format": "%(message)s"},
                "general": {"format": "[%(asctime)s] %(module)s [%(levelname)s] %(message)s"},
            },
            "handlers": {
                "general": {
                    "level": logging.DEBUG,
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": pathlib.Path(app.config.get("LOGS_DIR")) / pathlib.Path("dds.log"),
                    "formatter": "general",
                    "maxBytes": 0x100000,
                    "backupCount": 15,
                },
                "actions": {
                    "level": logging.INFO,
                    "class": "logging.handlers.RotatingFileHandler",
                    "maxBytes": 0x100000,
                    "backupCount": 15,
                    "filename": pathlib.Path(app.config.get("LOGS_DIR"))
                    / pathlib.Path("actions.log"),
                    "formatter": "default",
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
                "actions": {
                    "handlers": ["actions"],
                    "level": logging.INFO,
                    "propagate": False,
                },
            },
        }
    )

    structlog.configure(
        processors=[
            # Merge the bindings from Thread-Local Context, a sort of global context storage.
            structlog.threadlocal.merge_threadlocal,
            # Mimics the level configuration of the standard logging lib.
            # e.g. logger.debug() event will be dropped if logging level is set to INFO or higher.
            structlog.stdlib.filter_by_level,
            # Add the name of the logger to event dict.
            structlog.stdlib.add_logger_name,
            # Add log level to event dict.
            structlog.stdlib.add_log_level,
            # Perform %-style formatting.
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Add a timestamp to the event dict in ISO 8601 format.
            structlog.processors.TimeStamper(fmt="iso"),
            # If the "stack_info" key in the event dict is true, remove it and
            # render the current stack trace in the "stack" key.
            structlog.processors.StackInfoRenderer(),
            # If the "exc_info" key in the event dict is either true or a
            # sys.exc_info() tuple, remove "exc_info" and render the exception
            # with traceback into the "exception" key.
            structlog.processors.format_exc_info,
            # If some value is in bytes, decode it to a unicode str.
            structlog.processors.UnicodeDecoder(),
            # Render the final event dict as JSON.
            structlog.processors.JSONRenderer(),
        ],
        # `wrapper_class` is the bound logger that you get back from
        # get_logger(). This one imitates `logging.Logger`.
        wrapper_class=structlog.stdlib.BoundLogger,
        # `logger_factory` is used to create wrapped loggers that are used for
        # OUTPUT. This one returns a `logging.Logger`. The final value (a JSON
        # string) from the final processor (`JSONRenderer`) will be passed to
        # the method of the same name as that you've called on the bound logger.
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Effectively freeze configuration after creating the first bound
        # logger.
        cache_logger_on_first_use=True,
    )


def create_app(testing=False, database_uri=None):
    try:
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
        if testing:
            # Simplifies testing as we don't test the session protection anyway
            login_manager.session_protection = "basic"

        @app.before_request
        def prepare():
            """Populate flask globals for template rendering"""
            flask.g.current_user = None
            flask.g.current_user_emails = None
            if auth.current_user():
                flask.g.current_user = auth.current_user().username
                flask.g.current_user_emails = auth.current_user().emails
            elif flask_login.current_user.is_authenticated:
                flask.g.current_user = flask_login.current_user.username
                flask.g.current_user_emails = flask_login.current_user.emails
            elif flask.request.authorization:
                flask.g.current_user = flask.request.authorization.get("username")
                flask.g.current_user_emails = flask.request.authorization.get("emails")

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

        if app.config["REVERSE_PROXY"]:
            app.wsgi_app = ProxyFix(app.wsgi_app)

        # Initialize limiter
        limiter._storage_uri = app.config.get("RATELIMIT_STORAGE_URL")
        limiter.init_app(app)

        # Initialize migrations
        migrate.init_app(app, db)

        # initialize OIDC
        oauth.init_app(app)
        oauth.register(
            "default_login",
            client_secret=app.config.get("OIDC_CLIENT_SECRET"),
            client_id=app.config.get("OIDC_CLIENT_ID"),
            server_metadata_url=app.config.get("OIDC_ACCESS_TOKEN_URL"),
            client_kwargs={"scope": "openid profile email"},
        )

        app.cli.add_command(fill_db_wrapper)
        app.cli.add_command(create_new_unit)
        app.cli.add_command(update_uploaded_file_with_log)
        app.cli.add_command(lost_files_s3_db)

        with app.app_context():  # Everything in here has access to sessions
            from dds_web.database import models

            # Need to import auth so that the modifications to the auth objects take place
            import dds_web.security.auth

            # Register blueprints
            from dds_web.api import api_blueprint
            from dds_web.web.root import pages
            from dds_web.web.user import auth_blueprint

            app.register_blueprint(api_blueprint, url_prefix="/api/v1")
            app.register_blueprint(pages, url_prefix="")
            app.register_blueprint(auth_blueprint, url_prefix="")

            # Set-up the scheduler
            app.config["SCHEDULER_JOBSTORES"] = {"default": SQLAlchemyJobStore(engine=db.engine)}
            scheduler.init_app(app)
            scheduler.start()

            ENCRYPTION_KEY_BIT_LENGTH = 256
            ENCRYPTION_KEY_CHAR_LENGTH = int(ENCRYPTION_KEY_BIT_LENGTH / 8)

            if len(app.config.get("SECRET_KEY")) != ENCRYPTION_KEY_CHAR_LENGTH:
                from dds_web.errors import KeyLengthError

                raise KeyLengthError(ENCRYPTION_KEY_CHAR_LENGTH)

            return app
    except sqlalchemy.exc.OperationalError as err:
        app.logger.exception("The database seems to be down.")
        sys.exit(1)


@click.command("init-db")
@click.argument("db_type", type=click.Choice(["production", "dev-small", "dev-big"]))
@flask.cli.with_appcontext
def fill_db_wrapper(db_type):

    if db_type == "production":
        from dds_web.database import models

        username = flask.current_app.config["SUPERADMIN_USERNAME"]
        password = flask.current_app.config["SUPERADMIN_PASSWORD"]
        name = flask.current_app.config["SUPERADMIN_NAME"]
        existing_user = models.User.query.filter_by(username=username).one_or_none()

        email = flask.current_app.config["SUPERADMIN_EMAIL"]
        existing_email = models.Email.query.filter_by(email=email).one_or_none()

        if existing_email:
            flask.current_app.logger.info(
                f"User with email '{email}' already exists, not creating user."
            )
        elif existing_user:
            if isinstance(existing_user, models.SuperAdmin):
                flask.current_app.logger.info(
                    f"Super admin with username '{username}' already exists, not creating user."
                )
        else:
            flask.current_app.logger.info(f"Adding Super Admin: {username} ({email})")
            new_super_admin = models.SuperAdmin(username=username, name=name, password=password)
            new_email = models.Email(email=email, primary=True)
            new_email.user = new_super_admin
            db.session.add(new_email)
            db.session.commit()
            flask.current_app.logger.info(f"Super Admin added: {username} ({email})")
    else:
        flask.current_app.logger.info("Initializing development db")
        assert flask.current_app.config["USE_LOCAL_DB"]

        if db_type == "dev-small":
            from dds_web.development.db_init import fill_db

            fill_db()
        elif db_type == "dev-big":
            import dds_web.development.factories

            dds_web.development.factories.create_all()

        flask.current_app.logger.info("DB filled")


@click.command("create-unit")
@click.option("--name", "-n", type=str, required=True)
@click.option("--public_id", "-p", type=str, required=True)
@click.option("--external_display_name", "-e", type=str, required=True)
@click.option("--contact_email", "-c", type=str, required=True)
@click.option("--internal_ref", "-ref", type=str, required=False)
@click.option("--safespring_endpoint", "-se", type=str, required=True)
@click.option("--safespring_name", "-sn", type=str, required=True)
@click.option("--safespring_access", "-sa", type=str, required=True)
@click.option("--safespring_secret", "-ss", type=str, required=True)
@click.option("--days_in_available", "-da", type=int, required=False, default=90)
@click.option("--days_in_expired", "-de", type=int, required=False, default=30)
@flask.cli.with_appcontext
def create_new_unit(
    name,
    public_id,
    external_display_name,
    contact_email,
    internal_ref,
    safespring_endpoint,
    safespring_name,
    safespring_access,
    safespring_secret,
    days_in_available,
    days_in_expired,
):
    """Create a new unit."""
    from dds_web.database import models

    new_unit = models.Unit(
        name=name,
        public_id=public_id,
        external_display_name=external_display_name,
        contact_email=contact_email,
        internal_ref=internal_ref or public_id,
        safespring_endpoint=safespring_endpoint,
        safespring_name=safespring_name,
        safespring_access=safespring_access,
        safespring_secret=safespring_secret,
        days_in_available=days_in_available,
        days_in_expired=days_in_expired,
    )
    db.session.add(new_unit)
    db.session.commit()

    flask.current_app.logger.info(f"Unit '{name}' created")


@click.command("update-uploaded-file")
@click.option("--project", "-p", type=str, required=True)
@click.option("--path-to-log-file", "-fp", type=str, required=True)
@flask.cli.with_appcontext
def update_uploaded_file_with_log(project, path_to_log_file):
    """Update file details that weren't properly uploaded to db from cli log"""
    import botocore
    from dds_web.database import models
    from dds_web import db
    from dds_web.api.api_s3_connector import ApiS3Connector
    import json

    proj_in_db = models.Project.query.filter_by(public_id=project).one_or_none()
    assert proj_in_db

    with open(path_to_log_file, "r") as f:
        log = json.load(f)
    errors = {}
    files_added = []
    for file, vals in log.items():
        status = vals.get("status")
        if not status or not status.get("failed_op") == "add_file_db":
            continue

        with ApiS3Connector(project=proj_in_db) as s3conn:
            try:
                _ = s3conn.resource.meta.client.head_object(
                    Bucket=s3conn.project.bucket, Key=vals["path_remote"]
                )
            except botocore.client.ClientError as err:
                if err.response["Error"]["Code"] == "404":
                    errors[file] = {"error": "File not found in S3", "traceback": err.__traceback__}
            else:
                file_object = models.File.query.filter(
                    sqlalchemy.and_(
                        models.File.name == sqlalchemy.func.binary(file),
                        models.File.project_id == proj_in_db.id,
                    )
                ).first()
                if file_object:
                    errors[file] = {"error": "File already in database."}
                else:
                    new_file = models.File(
                        name=file,
                        name_in_bucket=vals["path_remote"],
                        subpath=vals["subpath"],
                        project_id=proj_in_db.id,
                        size_original=vals["size_raw"],
                        size_stored=vals["size_processed"],
                        compressed=not vals["compressed"],
                        public_key=vals["public_key"],
                        salt=vals["salt"],
                        checksum=vals["checksum"],
                    )
                    new_version = models.Version(
                        size_stored=new_file.size_stored, time_uploaded=datetime.datetime.utcnow()
                    )
                    proj_in_db.file_versions.append(new_version)
                    proj_in_db.files.append(new_file)
                    new_file.versions.append(new_version)

                    db.session.add(new_file)
                    files_added.append(new_file)
                db.session.commit()

        flask.current_app.logger.info(f"Files added: {files_added}")
        flask.current_app.logger.info(f"Errors while adding files: {errors}")


@click.command("lost-files")
@click.argument("action_type", type=click.Choice(["find", "list", "delete"]))
@flask.cli.with_appcontext
def lost_files_s3_db(action_type: str):
    """
    Identify (and optionally delete) files that are present in S3 or in the db, but not both.

    Args:
        action_type (str): "find", "list", or "delete"
    """
    from dds_web.database import models
    import boto3

    for unit in models.Unit.query:
        session = boto3.session.Session()

        resource = session.resource(
            service_name="s3",
            endpoint_url=unit.safespring_endpoint,
            aws_access_key_id=unit.safespring_access,
            aws_secret_access_key=unit.safespring_secret,
        )

        db_count = 0
        s3_count = 0
        for project in unit.projects:
            try:
                s3_filenames = set(
                    entry.key for entry in resource.Bucket(project.bucket).objects.all()
                )
            except resource.meta.client.exceptions.NoSuchBucket:
                flask.current_app.logger.warning("Missing bucket %s", project.bucket)
                continue

            try:
                db_filenames = set(entry.name_in_bucket for entry in project.files)
            except sqlalchemy.exc.OperationalError:
                flask.current_app.logger.critical("Unable to connect to db")

            diff_db = db_filenames.difference(s3_filenames)
            diff_s3 = s3_filenames.difference(db_filenames)
            if action_type == "list":
                for file_entry in diff_db:
                    flask.current_app.logger.info(
                        "Entry %s (%s, %s) not found in S3", file_entry, project, unit
                    )
                for file_entry in diff_s3:
                    flask.current_app.logger.info(
                        "Entry %s (%s, %s) not found in database", file_entry, project, unit
                    )
            elif action_type == "delete":
                # s3 can only delete 1000 objects per request
                batch_size = 1000
                s3_to_delete = list(diff_s3)
                for i in range(0, len(s3_to_delete), batch_size):
                    resource.meta.client.delete_objects(
                        Bucket=project.bucket,
                        Delete={
                            "Objects": [
                                {"Key": entry} for entry in s3_to_delete[i : i + batch_size]
                            ]
                        },
                    )

                db_entries = models.File.query.filter(
                    sqlalchemy.and_(
                        models.File.name_in_bucket.in_(diff_db),
                        models.File.project_id == project.id,
                    )
                )
                for db_entry in db_entries:
                    try:
                        for db_entry_version in db_entry.versions:
                            if db_entry_version.time_deleted is None:
                                db_entry_version.time_deleted = datetime.datetime.utcnow()
                        db.session.delete(db_entry)
                        db.session.commit()
                    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError):
                        db.session.rollback()
                        flask.current_app.logger.critical("Unable to delete the database entries")
                        sys.exit(1)

            # update the counters at the end of the loop to have accurate numbers for delete
            s3_count += len(diff_s3)
            db_count += len(diff_db)

    if s3_count or db_count:
        action_word = "Found" if action_type in ("find", "list") else "Deleted"
        flask.current_app.logger.info(
            "%s %d entries for lost files (%d in db, %d in s3)",
            action_word,
            s3_count + db_count,
            db_count,
            s3_count,
        )
        if action_type in ("find", "list"):
            sys.exit(1)

    else:
        flask.current_app.logger.info("Found no lost files")
