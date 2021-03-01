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
import botocore

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

        url, keys, bucketname, message = api_s3_connector.ApiS3Connector.get_s3_info(
            safespring_project=current_user.safespring,
            project_id=project["id"]
        )

        if any(x is None for x in [url, keys, bucketname]):
            return flask.make_response(f"No s3 info returned! {message}", 500)

        return flask.jsonify({"safespring_project": current_user.safespring,
                              "url": url,
                              "keys": keys,
                              "bucket": bucketname})
