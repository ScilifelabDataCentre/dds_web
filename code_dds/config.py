"""Configuration"""

# IMPORTS ########################################################### IMPORTS #

# Standard Library
from os import environ, path

# Installed
from dotenv import load_dotenv

# Own modules


# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))


# CLASSES ########################################################### CLASSES #


class Config:
    """Set Flask configuration from .env file."""

    # General Config
    SECRET_KEY = environ.get('SECRET_KEY')
    # FLASK_APP = environ.get('FLASK_APP')
    FLASK_ENV = environ.get('FLASK_ENV')

    # Database
    SQLALCHEMY_DATABASE_URI = environ.get("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SITE_NAME = 'Data Delivery System'
