"""S3 module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import pathlib

# Installed
import flask_restful
import flask
import sqlalchemy
import json

# Own modules
from code_dds.api.user import token_required
from code_dds.common.db_code import models
from code_dds.api.project import project_access_required
from code_dds.api import api_s3_connector

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


class S3Info(flask_restful.Resource):
    """Gets the projects S3 keys"""
    method_decorators = [project_access_required, token_required]

    def get(self, current_user, project, *args, **kwargs):
        """Get the safespring project"""

        s3conn = api_s3_connector.ApiS3Connector(
            safespring_project=current_user.safespring,
            project=project
        )

        if None in [s3conn.url, s3conn.keys, s3conn.bucketname]:
            return flask.make_response(
                "No s3 info returned! " + s3conn.message, 500
            )

        response = {"safespring_project": current_user.safespring,
                    "url": s3conn.url,
                    "keys": s3conn.keys,
                    "bucket": s3conn.bucketname}

        s3conn = None

        return flask.jsonify(response)
