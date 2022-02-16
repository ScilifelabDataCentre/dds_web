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

# initiate logging
action_logger = structlog.getLogger("actions")


####################################################################################################
# DECORATORS ########################################################################## DECORATORS #
####################################################################################################

# S3 ########################################################################################## S3 #


def project_optional(func):
    """Verify that user has access to project."""

    @functools.wraps(func)
    def verify_access(*args, **kwargs):
        """Check for access."""

        project_info = flask.request.args
        if project_info and project_info.get("project"):
            project = project_schemas.ProjectRequiredSchema().load(project_info)
        else:
            project = None

        return func(*args, project=project, **kwargs)

    return verify_access


def renew_access_required(func):
    """Check that user has permission to give access to another user in this project."""

    @functools.wraps(func)
    def access_decorator(*args, user, project, **kwargs):
        """Check if the current user has access to renew project access."""
        # Get roles
        current_user_role = auth.current_user().role
        other_user_role = user.role

        # Check if Researcher and if so is project owner or not
        if other_user_role == "Researcher" and project:
            project_user_row = models.ProjectUsers.query.filter_by(
                project_id=project.id, user_id=user.username
            ).one_or_none()
            if project_user_row and project_user_row.owner:
                other_user_role = "Project Owner"

        # Check access
        if (
            (
                current_user_role in "Unit Admin"
                and other_user_role
                not in ["Unit Admin", "Unit Personnel", "Project Owner", "Researcher"]
            )
            or (
                current_user_role == "Unit Personnel"
                and other_user_role not in ["Unit Personnel", "Project Owner", "Researcher"]
            )
            or (
                current_user_role == "Project Owner"
                and other_user_role not in ["Project Owner", "Researcher"]
            )
        ):
            raise AccessDeniedError(
                message=(
                    "You do not have the necessary permissions "
                    "to shared project access with this user."
                )
            )

        return func(*args, user=user, project=project, **kwargs)

    return access_decorator


def user_required(func):
    """Specify that the user object is required information."""

    @functools.wraps(func)
    def get_other_user(*args, **kwargs):
        """Get the user object from the database."""
        extra_args = flask.request.json
        if not extra_args:
            raise DDSArgumentError(message="Required information missing.")

        user_email = extra_args.pop("email")
        if not user_email:
            raise DDSArgumentError(message="User email missing.")

        user = user_schemas.UserSchema().load({"email": user_email})
        if not user:
            raise NoSuchUserError()

        return func(*args, **kwargs, user=user)

    return get_other_user


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
