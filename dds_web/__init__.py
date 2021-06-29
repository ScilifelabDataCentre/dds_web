"""Initialize Flask app."""

# IMPORTS ########################################################### IMPORTS #

# Standard library
from datetime import datetime, timedelta
import pytz
import logging
import os

# Installed
from flask import Flask, g, render_template, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_marshmallow import Marshmallow
from logging.handlers import RotatingFileHandler
from authlib.integrations import flask_client as auth_flask_client

# Own modules


# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #

app = Flask(__name__, instance_relative_config=False)
db = SQLAlchemy()
ma = Marshmallow(app)
C_TZ = pytz.timezone("Europe/Stockholm")
oauth = auth_flask_client.OAuth(app)

# FUNCTIONS ####################################################### FUNCTIONS #


@app.before_request
def prepare():
    # Test line for global
    g.current_user = session.get("current_user")
    g.current_user_id = session.get("current_user_id")
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

    # Set logger, to be used in the app
    log_file = os.path.join(app.config.get("LOGS_DIR"), "dds.log")
    log_formatter = logging.Formatter("%(asctime)s %(module)s [%(levelname)s] %(message)s")
    handler = RotatingFileHandler(log_file, maxBytes=100000000, backupCount=1)
    handler.setFormatter(log_formatter)
    app.logger.addHandler(handler)

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
                print(f"-----------------{err}", flush=True)

        from dds_web.api import api_blueprint

        app.register_blueprint(api_blueprint, url_prefix="/api/v1")

        from user import user_blueprint

        app.register_blueprint(user_blueprint, url_prefix="/user")

        from admin import admin_blueprint

        app.register_blueprint(admin_blueprint, url_prefix="/admin")

        from project import project_blueprint

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
