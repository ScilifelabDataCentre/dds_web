"""File related schemas."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import os

# Installed
import flask
import marshmallow
import sqlalchemy
import immutabledict

# Own modules
from dds_web import db
from dds_web.api import errors as ddserr
from dds_web import auth
import dds_web.security.auth
from dds_web.database import models
from dds_web import utils

####################################################################################################
# SCHEMAS ################################################################################ SCHEMAS #
####################################################################################################
