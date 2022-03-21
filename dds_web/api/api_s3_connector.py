"""API S3 Connector module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import logging
import traceback

# Installed

# Own modules
from dds_web.api.dds_decorators import (
    connect_cloud,
    bucket_must_exists,
)

from dds_web.database import models


####################################################################################################
# LOGGING ################################################################################ LOGGING #
####################################################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


class ApiS3Connector:
    """Connects to Simple Storage Service."""

    def __init__(self, project=None):
        self.project = project
        self.resource = None

    @connect_cloud
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def get_s3_info(self):
        """Get information required to connect to cloud."""
        endpoint, name, accesskey, secretkey = (
            models.Unit.query.filter_by(id=self.project.responsible_unit.id)
            .with_entities(
                models.Unit.safespring_endpoint,
                models.Unit.safespring_name,
                models.Unit.safespring_access,
                models.Unit.safespring_secret,
            )
            .one_or_none()
        )
        bucket = self.project.bucket

        return (
            name,
            {"access_key": accesskey, "secret_key": secretkey},
            endpoint,
            bucket,
        )

    @bucket_must_exists
    def remove_bucket(self, *args, **kwargs):
        """Removes all contents from the project specific s3 bucket."""
        # Get bucket object
        bucket = self.resource.Bucket(self.project.bucket)

        # Delete objects first
        bucket.objects.all().delete()

        # Delete bucket
        bucket.delete()
        bucket = None

    @bucket_must_exists
    def remove_multiple(self, items, batch_size: int = 1000, *args, **kwargs):
        """Removes all with prefix."""
        # s3 can only delete 1000 objects per request
        for i in range(0, len(items), batch_size):
            _ = self.resource.meta.client.delete_objects(
                Bucket=self.project.bucket,
                Delete={"Objects": [{"Key": x} for x in items[i : i + batch_size]]},
            )

    @bucket_must_exists
    def remove_one(self, file, *args, **kwargs):
        """Removes file from s3"""
        _ = self.resource.meta.client.delete_object(Bucket=self.project.bucket, Key=file)

    def generate_get_url(self, key):
        """Generate presigned urls for get requests."""

        # This does not perform any requests, the signing is "local"
        # and it doesn't check if the item exists before creating the link
        url = self.resource.meta.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.project.bucket, "Key": key},
            ExpiresIn=604800,  # 7 days in seconds
        )
        return url
