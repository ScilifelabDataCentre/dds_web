"""Decorators used with the DDS."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import functools

# Installed
import boto3
import botocore

# Own modules
from dds_web.api.errors import BucketNotFoundError

####################################################################################################
# DECORATORS ########################################################################## DECORATORS #
####################################################################################################

# S3 ########################################################################################## S3 #


def connect_cloud(func):
    """Connect to S3"""

    @functools.wraps(func)
    def init_resource(self, *args, **kwargs):

        _, self.keys, self.url, self.bucketname = self.get_s3_info()
        if None in [self.keys, self.url]:
            self.keys, self.url, self.bucketname, self.message = (
                None,
                None,
                None,
                self.message,
            )
        else:
            # Connect to service
            try:
                session = boto3.session.Session()

                self.resource = session.resource(
                    service_name="s3",
                    endpoint_url=self.url,
                    aws_access_key_id=self.keys["access_key"],
                    aws_secret_access_key=self.keys["secret_key"],
                )
            except botocore.client.ClientError as err:
                self.keys, self.url, self.bucketname, self.message = (
                    None,
                    None,
                    None,
                    err,
                )

        return func(self, *args, **kwargs)

    return init_resource


def bucket_must_exists(func):
    """Checks if the bucket exists"""

    @functools.wraps(func)
    def check_bucket_exists(self, *args, **kwargs):
        try:
            self.resource.meta.client.head_bucket(Bucket=self.bucketname)
        except botocore.client.ClientError as err:
            raise BucketNotFoundError(message=str(err))

        return func(self, *args, **kwargs)

    return check_bucket_exists
