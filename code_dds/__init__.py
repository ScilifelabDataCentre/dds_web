"""Initialize Flask app."""

# IMPORTS ########################################################### IMPORTS #

# Standard library
import pytz
from datetime import datetime, timedelta

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
    ## Test line for global
    g.current_user = session.get('current_user')

def create_app():
    """Construct the core application."""

    app.config.from_object('config.Config')

    db.init_app(app)    # Initialize database
    ma.init_app(app)

    with app.app_context():     # Everything in here has access to sessions        
        from code_dds import routes  # Import routes

        db.drop_all()       # Make sure it's the latest db
        db.create_all()     # Create database tables for our data models

        from code_dds.development.db_init import fill_db
        fill_db()           # Fill db with initial entries (for development)

        from api import api_blueprint
        app.register_blueprint(api_blueprint)
        
        from user import user_blueprint
        app.register_blueprint(user_blueprint)

        return app


def timestamp(dts = None) -> (str):
    '''Gets the current time. Formats timestamp.

    Returns:
        str:    Timestamp in format 'YY-MM-DD_HH-MM-SS'

    '''

    now = datetime.now(tz=C_TZ) if dts is None else dts
    ts = str(now.strftime('%Y-%m-%d %H:%M:%S.%f%z'))
    
    # for t in (now.year, "-", now.month, "-", now.day, " ",
    #           now.hour, ":", now.minute, ":", now.second):
    #     if len(str(t)) == 1 and isinstance(t, int):
    #         timestamp += f"0{t}"
    #     else:
    #         timestamp += f"{t}"

    return ts


def token_expiration(valid_time: int = 48):
    now = datetime.now(tz=C_TZ)
    expire = now + timedelta(hours=valid_time)
    
    return timestamp(dts=expire)
    
