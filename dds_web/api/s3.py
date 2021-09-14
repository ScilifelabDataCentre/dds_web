"""S3 module"""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library

# Installed
import flask_restful
import flask

# Own modules
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.dds_decorators import token_required, project_access_required

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class S3Info(flask_restful.Resource):
    """Gets the projects S3 keys"""

    method_decorators = [project_access_required, token_required]

    def get(self, current_user, _):
        """Get the safespring project"""

        sfsp_proj, keys, url, bucketname, message = ApiS3Connector().get_s3_info()

        if any(x is None for x in [url, keys, bucketname]):
            return flask.make_response(f"No s3 info returned! {message}", 500)

        return flask.jsonify(
            {
                "safespring_project": sfsp_proj,
                "url": url,
                "keys": keys,
                "bucket": bucketname,
            }
        )
