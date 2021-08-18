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

import pathlib
import json

# Installed
import boto3
import botocore
import flask  # used

# Own modules
from dds_web import app
from dds_web.database import models
from dds_web.api.dds_decorators import (
    connect_cloud,
    bucket_must_exists,
    token_required,
    project_access_required,
)
from dds_web.api.errors import (
    ItemDeletionError,
    MissingTokenOutputError,
    BucketNotFoundError,
    DatabaseError,
    DeletionError,
    S3ProjectNotFoundError,
    S3InfoNotFoundError,
    KeyNotFoundError,
    S3ConnectionError,
)


###############################################################################
# LOGGING ########################################################### LOGGING #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


@token_required
@project_access_required
class ApiS3Connector:
    """Connects to Simple Storage Service."""

    def __init__(self, *args, **kwargs):
        try:
            self.current_user, self.project = args
            (
                self.safespring,
                self.keys,
                self.url,
                self.bucketname,
            ) = self.get_s3_info()
            self.resource = None

        except (ValueError, IOError, AssertionError, FileNotFoundError) as err:
            raise S3ConnectionError(message=str(err))
        except (
            MissingTokenOutputError,
            BucketNotFoundError,
            DatabaseError,
            S3ProjectNotFoundError,
            KeyNotFoundError,
        ):
            raise

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

        safespring_project = None
        from dds_web.api.db_connector import DBConnector

        try:
            with DBConnector() as dbconn:
                safespring_project = dbconn.cloud_project()
                app.logger.debug(f"Safespring project: {safespring_project}")

                if not safespring_project:
                    raise S3ProjectNotFoundError(
                        username=self.current_user.username, project=self.project.get("id")
                    )
        except (MissingTokenOutputError, S3ProjectNotFoundError, DatabaseError):
            raise

        s3keys = {}
        bucketname = None
        # 1. Get keys
        # TODO (ina): Change -- these should not be saved in file
        # print(flask.current_app.config["DDS_S3_CONFIG"], flush=True)
        s3_config_path = flask.current_app.config.get("DDS_S3_CONFIG")
        if not s3_config_path:
            raise S3InfoNotFoundError(message="API failed getting the s3 config file path.")

        s3path = pathlib.Path(s3_config_path)

        if not s3path.exists():
            raise FileNotFoundError("DDS S3 config file not found.")

        try:
            with s3path.open(mode="r") as f:
                s3keys = json.load(f).get("sfsp_keys").get(safespring_project)

            # 2. Get endpoint url
            with s3path.open(mode="r") as f:
                endpoint_url = json.load(f).get("endpoint_url")

            if None in [s3keys.get("access_key"), s3keys.get("secret_key")]:
                raise KeyNotFoundError(
                    "Safespring S3 access or secret key not found in s3 config file."
                )

        except KeyNotFoundError:
            raise

        try:
            with DBConnector() as dbconn:
                # 3. Get bucket name
                bucketname = dbconn.get_bucket_name()
        except (MissingTokenOutputError, BucketNotFoundError, DatabaseError):
            raise

        app.logger.debug(f"{s3keys}")
        return safespring_project, s3keys, endpoint_url, bucketname

    def get_safespring_project(self):
        """Get the safespring project"""

    @bucket_must_exists
    def remove_all(self, *args, **kwargs):
        """Removes all contents from the project specific s3 bucket."""

        try:
            bucket = self.resource.Bucket(self.bucketname)
            bucket.objects.all().delete()
        except botocore.client.ClientError as err:
            raise DeletionError(message=str(err), username=None, project=self.project.get("id"))
        else:
            return True

    @bucket_must_exists
    def remove_folder(self, folder, *args, **kwargs):
        """Removes all with prefix."""

        removed, error = (False, "")
        try:
            self.resource.Bucket(self.bucketname).objects.filter(Prefix=f"{folder}/").delete()
        except botocore.client.ClientError as err:
            error = str(err)
        else:
            removed = True

        return removed, error

    @bucket_must_exists
    def remove_one(self, file, *args, **kwargs):
        """Removes file from s3"""

        removed, error = (False, "")
        try:
            _ = self.resource.meta.client.delete_object(Bucket=self.bucketname, Key=file)
        except botocore.client.ClientError as err:
            error = str(err)
        else:
            removed = True

        return removed, error
