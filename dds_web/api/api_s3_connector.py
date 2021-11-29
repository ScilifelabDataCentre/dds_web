"""API S3 Connector module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import logging
import traceback
import pathlib
import json

# Installed
import botocore
import flask
import sqlalchemy

# Own modules
from dds_web.api.dds_decorators import (
    connect_cloud,
    bucket_must_exists,
)
from dds_web.api.errors import (
    BucketNotFoundError,
    DatabaseError,
    DeletionError,
    S3ProjectNotFoundError,
    S3InfoNotFoundError,
    KeyNotFoundError,
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

        try:
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
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise DatabaseError from sqlerr

        return (
            name,
            {"access_key": accesskey, "secret_key": secretkey},
            endpoint,
            bucket,
        )

    @bucket_must_exists
    def remove_all(self, *args, **kwargs):
        """Removes all contents from the project specific s3 bucket."""

        try:
            bucket = self.resource.Bucket(self.project.bucket)
            bucket.objects.all().delete()
        except botocore.client.ClientError as err:
            raise DeletionError(message=str(err), project=self.project.get("id"))
        else:
            return True

    @bucket_must_exists
    def remove_folder(self, folder, *args, **kwargs):
        """Removes all with prefix."""

        removed, error = (False, "")
        try:
            self.resource.Bucket(self.project.bucket).objects.filter(Prefix=f"{folder}/").delete()
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
            _ = self.resource.meta.client.delete_object(Bucket=self.project.bucket, Key=file)
        except botocore.client.ClientError as err:
            error = str(err)
        else:
            removed = True

        return removed, error

    def generate_get_url(self, keys):
        """Generate presigned urls for get requests."""

        if len(keys) == 1:
            try:
                self.resource.meta.client.head_object(Bucket=self.project.bucket, Key=key[0])
            except botocore.exceptions.ClientError:
                # Not found, can't get url
                return

            url = self.resource.meta.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.project.bucket, "Key": key[0]},
                ExpiresIn=36000,
            )
            return url

        paginator = self.resource.meta.client.get_paginator("list_objects")
        pages = paginator.paginate(Bucket=self.project.bucket)

        items_to_find = ""
        for page in pages:
            keys_in_s3 = set(x["Key"] for x in page["Contents"])
            # for

    def bucket_items(self):
        """Check if keys exist in bucket and return those that aren't."""

        # flask.current_app.logger.debug(items)
        # Paginator iterates 1000 items at a time through the bucket contents
        paginator = self.resource.meta.client.get_paginator("list_objects")
        pages = paginator.paginate(Bucket=self.project.bucket)

        # found_in_bucket = {}
        # Yield 1000 items at a time
        for page in pages:
            keys_in_s3 = set(x["Key"] for x in page["Contents"])
            yield keys_in_s3
            # for loc, files in list(items.items()):
            #     names_in_bucket = {y.name_in_bucket: {"obj": y, "loc": loc} for y in files}
            #     flask.current_app.logger.debug(names_in_bucket)

            #     for x, y in names_in_bucket.items():
            #         if x in keys_in_s3:
            #             items[loc].remove(y["obj"])
            # [
            #     items[loc].remove(x["obj"])
            #     for x in {y.name_in_bucket: {"obj": y, "loc": loc} for y in files}
            #     if x in keys_in_s3
            # ]
            # [
            #     items[loc].remove(x)
            #     for x in keys_in_s3.intersection({y.name_in_bucket for y in files})
            # ]
            # flask.current_app.logger.debug(f"items after {loc}: {items}")

            #     {x for x in files if x.name_in_bucket in keys_in_s3}
            # [items.pop(x) for x in keys_in_s3.intersection(items)]
        #     if not items:
        #         break
        # return
        # if items:
        #     flask.current_app.logger.warning(
        #         f"The following items were not found in the bucket: {items}"
        #     )

        # return items
