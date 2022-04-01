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
from dds_web import db
from dds_web.errors import (
    BucketNotFoundError,
    DatabaseError,
    DDSArgumentError,
    LoggedHTTPException,
    MissingJsonError,
    S3ConnectionError,
)
from dds_web.utils import get_username_or_request_ip

# initiate logging
action_logger = structlog.getLogger("actions")


####################################################################################################
# DECORATORS ########################################################################## DECORATORS #
####################################################################################################


def handle_validation_errors(func):
    @functools.wraps(func)
    def handle_error(*args, **kwargs):

        try:
            result = func(*args, **kwargs)
        except (marshmallow.exceptions.ValidationError) as valerr:
            if "_schema" in valerr.messages:
                return valerr.messages["_schema"][0], 400
            else:
                return valerr.messages, 400

        return result

    return handle_error


def json_required(func):
    @functools.wraps(func)
    def verify_json(*args, **kwargs):

        if not flask.request.json:
            raise MissingJsonError(message="Required data missing from request!")

        return func(*args, **kwargs)

    return verify_json


def args_required(func):
    @functools.wraps(func)
    def verify_args(*args, **kwargs):

        if not flask.request.args:
            raise DDSArgumentError(message="Required information missing from request!")

        return func(*args, **kwargs)

    return verify_args


def dbsession(func):
    @functools.wraps(func)
    def make_commit(*args, **kwargs):

        # Run function, catch errors
        try:
            result = func(*args, **kwargs)
        except sqlalchemy.exc.OperationalError as err:
            raise DatabaseError(message=str(err), alt_message="Unexpected database error.")
        except:
            db.session.rollback()
            raise

        # If ok, commit any changes
        try:
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise DatabaseError(
                message=str(sqlerr), alt_message="Saving database changes failed."
            ) from sqlerr

        return result

    return make_commit


def handle_db_error(func):
    @functools.wraps(func)
    def perform_get(*args, **kwargs):

        # Run function, catch errors
        try:
            result = func(*args, **kwargs)
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError) as sqlerr:
            flask.current_app.logger.exception(sqlerr)
            raise DatabaseError(
                message=str(sqlerr),
                alt_message=(
                    "Database malfunction!"
                    if isinstance(sqlerr, sqlalchemy.exc.OperationalError)
                    else None
                ),
            ) from sqlerr

        return result

    return perform_get


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
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError) as sqlerr:
            raise DatabaseError(
                message=str(sqlerr),
                alt_message=(
                    "Could not connect to cloud"
                    + (
                        ": Database malfunction."
                        if isinstance(sqlerr, sqlalchemy.exc.OperationalError)
                        else "."
                    ),
                ),
            ) from sqlerr
        except botocore.client.ClientError as clierr:
            raise S3ConnectionError(message=str(clierr)) from clierr

        return func(self, *args, **kwargs)

    return init_resource


def bucket_must_exists(func):
    """Checks if the bucket exists"""

    @functools.wraps(func)
    def check_bucket_exists(self, *args, **kwargs):
        try:
            self.resource.meta.client.head_bucket(Bucket=self.bucketname)
        except botocore.client.ClientError as err:
            raise BucketNotFoundError(message=str(err)) from err

        return func(self, *args, **kwargs)

    return check_bucket_exists


def logging_bind_request(func):
    """Binds some request parameters to the thread-local context of structlog"""

    @functools.wraps(func)
    def wrapper_logging_bind_request(*args, **kwargs):
        with structlog.threadlocal.bound_threadlocal(
            resource=flask.request.path or "not applicable",
            project=flask.request.args.get("project") if flask.request.args else None,
            user=get_username_or_request_ip(),
        ):

            try:
                value = func(*args, **kwargs)

                if hasattr(value, "status"):
                    structlog.threadlocal.bind_threadlocal(response=value.status)

                action_logger.info(f"{flask.request.endpoint}.{func.__name__}")
                # make sure the threadlocal state is pruned after the log was written.
                structlog.threadlocal.clear_threadlocal()
                return value

            except Exception as err:
                if not isinstance(err, LoggedHTTPException):
                    # HTTPExceptions are already logged as warnings, no need to log twice.
                    action_logger.exception(
                        f"Uncaught exception in {flask.request.endpoint}.{func.__name__}",
                        stack_info=True,
                    )
                raise

    return wrapper_logging_bind_request
