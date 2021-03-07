"""Initialize Flask app."""

# IMPORTS ########################################################### IMPORTS #

# Standard library
from datetime import datetime, timedelta
import pytz

# Installed
from flask import Flask, g, render_template, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_marshmallow import Marshmallow

# Own modules


# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #

app = Flask(__name__, instance_relative_config=False)
db = SQLAlchemy()
ma = Marshmallow(app)
C_TZ = pytz.timezone('Europe/Stockholm')


# FUNCTIONS ####################################################### FUNCTIONS #

@app.before_request
def prepare():
    # Test line for global
    g.current_user = session.get('current_user')
    g.current_user_id = session.get('current_user_id')
    g.is_facility = session.get('is_facility')
    if g.is_facility:
        g.facility_name = session.get('facility_name')


def create_app():
    """Construct the core application."""

    app.config.from_object('config.Config')

    db.init_app(app)    # Initialize database
    # ma.init_app(app)

    with app.app_context():     # Everything in here has access to sessions
        from code_dds import routes  # Import routes
        from code_dds.db_code import models

        # db.drop_all()       # Make sure it's the latest db
        db.create_all()     # Create database tables for our data models

        # puts in test info for local DB, will be removed later
        if app.config['USE_LOCAL_DB']:
            try:
                from code_dds.development.db_init import fill_db
                fill_db()
            except Exception as err:
                # don't care why, this will be removed soon anyway
                print(f"-----------------{err}", flush=True)

        from code_dds.api import api_blueprint
        app.register_blueprint(api_blueprint, url_prefix='/api/v1')

        from user import user_blueprint
        app.register_blueprint(user_blueprint, url_prefix='/user')

        from project import project_blueprint
        app.register_blueprint(project_blueprint, url_prefix='/project')

        return app


def timestamp(dts=None) -> (str):
    '''Gets the current time. Formats timestamp.

    Returns:
        str:    Timestamp in format 'YY-MM-DD_HH-MM-SS'

    '''

    now = datetime.now(tz=C_TZ) if dts is None else dts
    t_s = str(now.strftime('%Y-%m-%d %H:%M:%S.%f%z'))

    return t_s


def token_expiration(valid_time: int = 48):
    now = datetime.now(tz=C_TZ)
    expire = now + timedelta(hours=valid_time)

    return timestamp(dts=expire)
