"""Decorators used with the DDS."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import functools

# Installed
import boto3
import botocore
import flask
import structlog
import sqlalchemy
import marshmallow

# Own modules
from dds_web import db, auth
from dds_web.errors import (
    BucketNotFoundError,
    DatabaseError,
    DDSArgumentError,
    NoSuchUserError,
    AccessDeniedError,
)
from dds_web.utils import get_username_or_request_ip
from dds_web.api.schemas import user_schemas, project_schemas
from dds_web.database import models

# initiate logging
action_logger = structlog.getLogger("actions")


####################################################################################################
# DECORATORS ########################################################################## DECORATORS #
####################################################################################################


def dbsession(func):
    @functools.wraps(func)
    def make_commit(*args, **kwargs):

        # Run function, catch errors
        try:
            result = func(*args, **kwargs)
        except:
            db.session.rollback()
            raise

        # If ok, commit any changes
        try:
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise DatabaseError(message=str(sqlerr), alt_message="Saving database changes failed.")

        return result

    return make_commit


# S3 ########################################################################################## S3 #


def connect_cloud(func):
    """Connect to S3"""

    @functools.wraps(func)
    def init_resource(self, *args, **kwargs):

        try:
            _, self.keys, self.url, self.bucketname = self.get_s3_info()
            # Connect to service
            session = boto3.session.Session()
            self.resource = session.resource(
                service_name="s3",
                endpoint_url=self.url,
                aws_access_key_id=self.keys["access_key"],
                aws_secret_access_key=self.keys["secret_key"],
            )
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise DatabaseError(message=str(sqlerr))
        except botocore.client.ClientError as clierr:
            raise S3ConnectionError(message=str(clierr))

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


def logging_bind_request(func):
    """Binds some request parameters to the thread-local context of structlog"""

    @functools.wraps(func)
    def wrapper_logging_bind_request(*args, **kwargs):
        with structlog.threadlocal.bound_threadlocal(
            resource=flask.request.path or "not applicable",
            project=flask.request.args.get("project"),
            user=get_username_or_request_ip(),
        ):
            value = func(*args, **kwargs)

            if hasattr(value, "status"):
                structlog.threadlocal.bind_threadlocal(response=value.status)

            action_logger.info(f"{flask.request.endpoint}.{func.__name__}")

            # make sure the threadlocal state is pruned after the log was written.
            structlog.threadlocal.clear_threadlocal()
            return value

    return wrapper_logging_bind_request
