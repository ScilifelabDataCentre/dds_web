"""S3 module"""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library

# Installed
import flask_restful
import flask
import sqlalchemy

# Own modules
from dds_web import auth
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.dds_decorators import logging_bind_request, handle_validation_errors
from dds_web.errors import (
    S3ProjectNotFoundError,
    DatabaseError,
)
from dds_web.api.schemas import project_schemas
from dds_web.api.files import check_eligibility_for_upload

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class S3Info(flask_restful.Resource):
    """Gets the projects S3 keys"""

    @auth.login_required(role=["Unit Admin", "Unit Personnel"])
    @logging_bind_request
    @handle_validation_errors
    def get(self):
        """Get the safespring project."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        check_eligibility_for_upload(status=project.current_status)

        try:
            sfsp_proj, keys, url, bucketname = ApiS3Connector(project=project).get_s3_info()
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError) as sqlerr:
            raise DatabaseError(
                message=str(sqlerr),
                alt_message="Could not get cloud information"
                + (
                    ": Database malfunction."
                    if isinstance(sqlerr, sqlalchemy.exc.OperationalError)
                    else "."
                ),
            ) from sqlerr

        if any(x is None for x in [url, keys, bucketname]):
            raise S3ProjectNotFoundError("No s3 info returned!")

        return {
            "safespring_project": sfsp_proj,
            "url": url,
            "keys": keys,
            "bucket": bucketname,
        }
