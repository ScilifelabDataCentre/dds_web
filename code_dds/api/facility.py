"""Facility related API endpoints."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library


# Installed
import flask
import flask_restful

# Own modules
from code_dds import marshmallows as marmal
from code_dds import models
from code_dds.api import login


###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################

class ListFacilities(flask_restful.Resource):
    """Lists all facilities in database."""

    def get(self):
        """Gets all facilities from db and return them in response."""

        all_facilities = models.Facility.query.all()
        return marmal.facs_schema.dump(all_facilities)
