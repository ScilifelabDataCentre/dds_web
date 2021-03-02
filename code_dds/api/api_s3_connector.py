"""API S3 Connector module"""

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

        if None in [self.keys, self.url]:
            self.keys, self.url, self.bucketname, self.message = (
                None, None, None, self.message
            )
        else:
            # Connect to service
            try:
                session = boto3.session.Session()

                self.resource = session.resource(
                    service_name="s3",
                    endpoint_url=self.url,
                    aws_access_key_id=self.keys["access_key"],
                    aws_secret_access_key=self.keys["secret_key"]
                )
            except botocore.client.ClientError as err:
                self.keys, self.url, self.bucketname, self.message = (
                    None, None, None, err
                )

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


@dataclasses.dataclass
class ApiS3Connector:
    """Connects to Simple Storage Service."""

    project_id: dataclasses.InitVar[str]
    safespring_project: str
    keys: dict = dataclasses.field(init=False)
    url: str = dataclasses.field(init=False)
    bucketname: str = dataclasses.field(init=False)
    resource = None

    def __post_init__(self, project_id):
        self.keys, self.url, self.bucketname, self.message = \
            self.get_s3_info(safespring_project=self.safespring_project,
                             project_id=project_id)

    @connect_cloud
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    @staticmethod
    def get_s3_info(safespring_project, project_id):
        """Get information required to connect to cloud."""

        # 1. Get keys
        try:
            # TODO (ina): Change -- these should not be saved in file
            s3path = pathlib.Path.cwd() / \
                pathlib.Path("sensitive/s3_config.json")
            with s3path.open(mode="r") as f:
                s3keys = json.load(f)["sfsp_keys"][safespring_project]
        except IOError as err:
            return None, None, None, f"Failed getting keys! {err}"

        # 2. Get endpoint url
        try:
            with s3path.open(mode="r") as f:
                endpoint_url = json.load(f)["endpoint_url"]
        except IOError as err:
            return None, None, None, f"Failed getting safespring url! {err}"

        if not all(x in s3keys for x in ["access_key", "secret_key"]):
            return None, None, None, "Keys not found!"

        # 3. Get bucket name
        try:
            bucket = models.Project.query.filter_by(
                id=project_id
            ).with_entities(
                models.Project.bucket
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            return None, None, None, f"Failed to get project bucket name! {err}"

        if not bucket or bucket is None:
            return None, None, None, "Project bucket not found!"

        return s3keys, endpoint_url, bucket[0], ""

    @bucket_must_exists
    def remove_all(self, *args, **kwargs):
        """Removes all contents from the project specific s3 bucket."""

        try:
            bucket = self.resource.Bucket(self.bucketname)
            bucket.objects.all().delete()
        except botocore.client.ClientError as err:
            return False, f"Failed removing all items from project: {err}"

        return True, ""

    @bucket_must_exists
    def remove_one(self, file, *args, **kwargs):
        """Removes file from s3"""

        try:
            response = self.resource.meta.client.delete_object(
                Bucket=self.bucketname,
                Key=file
            )
        except botocore.client.ClientError as err:
            return False, f"Failed to remove item {file}: {err}"

        return True, ""
