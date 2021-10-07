"""S3 module"""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library

# Installed
import flask_restful
import flask

# Own modules
from dds_web import auth
from dds_web.utils import verify
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api import marshmallows

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class S3Info(flask_restful.Resource):
    """Gets the projects S3 keys"""

    @auth.login_required
    def get(self):
        """Get the safespring project"""

        project, safespring_project, endpoint_url, s3_keys = marshmallows.S3KeySchema().load(
            flask.request.args
        )

        return flask.jsonify(
            {
                "safespring_project": safespring_project,
                "url": endpoint_url,
                "keys": s3_keys,
                "bucket": getattr(project, "bucket"),
            }
        )
