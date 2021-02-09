"""S3-related API endpoints."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import json
import pathlib

# Installed
import flask_restful

# Own modules
from code_dds.db_code import marshmallows as marmal
from code_dds.db_code import models


###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################

# class ListS3(flask_restful.Resource):
#     """Endpoint for listing all S3 projects in the database."""

#     def get(self):
#         """Gets S3 projects from database and returns in request response."""

#         all_s3projects = models.S3Project.query.all()
#         return marmal.s3s_schema.dump(all_s3projects)   


class S3Info(flask_restful.Resource):
    """Endpoint for getting S3 connection information."""

    def get(self):
        """Gets the information from file (atm, will be changed) and returns
        json response."""

        
        s3path = pathlib.Path.cwd() / \
            pathlib.Path("sensitive/s3_config.json")
        with s3path.open(mode="r") as f:
            s3creds = json.load(f)

        return s3creds
