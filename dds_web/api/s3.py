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
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.errors import (
    S3ProjectNotFoundError,
)
from dds_web.api.schemas import project_schemas

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class S3Info(flask_restful.Resource):
    """Gets the projects S3 keys"""

    @auth.login_required
    def get(self):
        """Get the safespring project"""

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        sfsp_proj, keys, url, bucketname = ApiS3Connector(project=project).get_s3_info()

        if any(x is None for x in [url, keys, bucketname]):
            raise S3ProjectNotFoundError(f"No s3 info returned! {message}")

        return flask.jsonify(
            {
                "safespring_project": sfsp_proj,
                "url": url,
                "keys": keys,
                "bucket": bucketname,
            }
        )
