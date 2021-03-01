"""S3 Connector module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import traceback

import sys
import dataclasses
import functools
# import requests
import pathlib
import json

# Installed
import boto3
import botocore
import sqlalchemy

# Own modules
from code_dds.common.db_code import models

###############################################################################
# LOGGING ########################################################### LOGGING #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################


def connect_cloud(func):
    """Connect to S3"""

    @functools.wraps(func)
    def init_resource(self, *args, **kwargs):

        # Connect to service
        try:
            session = boto3.session.Session()

            self.resource = session.resource(
                service_name="s3",
                endpoint_url=self.url,
                aws_access_key_id=self.keys["access_key"],
                aws_secret_access_key=self.keys["secret_key"]
            )
        except botocore.client.ClientError:
            return None

        return func(self, *args, **kwargs)

    return init_resource


def bucket_must_exists(func):
    """Checks if the bucket exists"""

    @functools.wraps(func)
    def check_bucket_exists(self, *args, **kwargs):
        try:
            self.resource.meta.client.head_bucket(Bucket=self.bucketname)
        except botocore.client.ClientError:
            return False,  f"Project does not yet have a " \
                "dedicated bucket in the S3 instance."

        return func(self, *args, **kwargs)

    return check_bucket_exists


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class ApiS3Connector:
    """Connects to Simple Storage Service."""

    def __init__(self, safespring_project, project):
        s3_info = self.get_s3_info(safespring_project=safespring_project,
                                   project=project)

        # Check that we have all information
        if not all(x in s3_info for x in ["keys", "url", "bucket"]):
            self.url = None
            self.keys = None
            self.bucketname = None
        else:
            self.url = s3_info["url"]
            self.keys = s3_info["keys"]
            self.bucketname = s3_info["bucket"]

        self.resource = None
        self.message = s3_info["message"] if "message" in s3_info else ""

    @connect_cloud
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    @staticmethod
    def get_s3_info(safespring_project, project):
        """Get information required to connect to cloud."""

        # Get keys
        try:
            # TODO (ina): Change -- these should not be saved in file
            s3path = pathlib.Path.cwd() / \
                pathlib.Path("sensitive/s3_config.json")
            with s3path.open(mode="r") as f:
                s3keys = json.load(f)["sfsp_keys"][safespring_project]
        except IOError as err:
            return {"message": f"Failed getting keys! {err}"}

        # Get endpoint url
        try:
            with s3path.open(mode="r") as f:
                endpoint_url = json.load(f)["endpoint_url"]
        except IOError as err:
            return {"message": f"Failed getting safespring url! {err}"}

        if not all(x in s3keys for x in ["access_key", "secret_key"]):
            return {"message": "Keys not found!"}

        # Get bucket name
        try:
            bucket = models.Project.query.filter_by(id=project["id"]).\
                with_entities(models.Project.bucket).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            return {"message": "Failed to get project bucket name! {err}"}

        if not bucket or bucket is None:
            return {"message": "Project bucket not found!"}

        return {"keys": s3keys, "url": endpoint_url,
                "bucket": bucket[0], "message": ""}

    @bucket_must_exists
    def remove_all(self, *args, **kwargs):
        """Removes all contents from the project specific s3 bucket."""

        try:
            bucket = self.resource.Bucket(self.bucketname)
            bucket.objects.all().delete()
        except botocore.client.ClientError as err:
            return False, f"Failed removing all items from project: {err}"

        return True, ""
