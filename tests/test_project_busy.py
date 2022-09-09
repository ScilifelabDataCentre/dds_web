# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http

# Own
from dds_web import db
from dds_web.database import models
import tests


# CONFIG ################################################################################## CONFIG #

proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}
not_busy_proj_query = {"project": "public_project_id"}
busy_proj_query = {"project": "restricted_project_id"}
# proj_query_restricted = {"project": "restricted_project_id"}

# TESTS #################################################################################### TESTS #
