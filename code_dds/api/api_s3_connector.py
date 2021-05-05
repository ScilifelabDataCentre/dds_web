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
import flask

# Own modules
from code_dds import app
from code_dds.db_code import models
from code_dds.api.dds_decorators import (
    connect_cloud,
    bucket_must_exists,
    token_required,
    project_access_required,
)
from code_dds.api.errors import ItemDeletionError

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

        except ValueError as err:
            flask.abort(500, str(err))

        (
            self.safespring,
            self.keys,
            self.url,
            self.bucketname,
            self.message,
        ) = self.get_s3_info()
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

        safespring = ""
        from code_dds.api.db_connector import DBConnector

        with DBConnector() as dbconn:
            safespring, error = dbconn.cloud_project()

        print(f"-- {safespring}", flush=True)

        s3keys, url, bucketname, error = (None,) * 3 + ("",)
        # 1. Get keys
        try:
            # TODO (ina): Change -- these should not be saved in file
            # print(flask.current_app.config["DDS_S3_CONFIG"], flush=True)
            s3path = pathlib.Path(flask.current_app.config["DDS_S3_CONFIG"])
            # s3path = pathlib.Path.cwd() / pathlib.Path("sensitive/s3_config.json")
            with s3path.open(mode="r") as f:
                s3keys = json.load(f).get("sfsp_keys").get(safespring)
                print(f"keys: {s3keys}", flush=True)
        except IOError as err:
            return s3keys, url, bucketname, f"Failed getting keys: {err}"

        # 2. Get endpoint url
        try:
            with s3path.open(mode="r") as f:
                endpoint_url = json.load(f)["endpoint_url"]
                print(f"Endpoint: {endpoint_url}", flush=True)
        except IOError as err:
            return s3keys, url, bucketname, f"Failed getting url! {err}"

        if not all(x in s3keys for x in ["access_key", "secret_key"]):
            return s3keys, url, bucketname, "Keys not found!"

        with DBConnector() as dbconn:
            # 3. Get bucket name
            bucketname, error = dbconn.get_bucket_name()

        print(s3keys, flush=True)
        return safespring, s3keys, endpoint_url, bucketname, error

    def get_safespring_project(self):
        """Get the safespring project"""

    @bucket_must_exists
    def remove_all(self, *args, **kwargs):
        """Removes all contents from the project specific s3 bucket."""

        removed, error = (False, "")
        try:
            bucket = self.resource.Bucket(self.bucketname)
            bucket.objects.all().delete()
        except botocore.client.ClientError as err:
            error = str(err)
        else:
            removed = True

        return removed, error

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
