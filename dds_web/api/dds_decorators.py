###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import functools
import logging

# Installed
import flask
import jwt
import boto3
import botocore
from sqlalchemy.sql import func
import sqlalchemy

# Own modules
from dds_web import app
from dds_web.database import models
from dds_web.api.errors import (
    MissingCredentialsError,
    TokenNotFoundError,
    JwtTokenDecodingError,
    DatabaseError,
    JwtTokenError,
    MissingProjectIDError,
    IncorrectDecoratorUsageException,
    BucketNotFoundError,
)
from dds_web import actions

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################

# AUTH ################################################################# AUTH #


def token_required(f):
    """Decorator function for verifying the JWT tokens in requests."""

    @functools.wraps(f)
    def validate_token(*args, **kwargs):
        token = None

        # Get the token from the header
        token = flask.request.headers.get("x-access-token")
        if not token:
            raise TokenNotFoundError

        # Verify the token
        try:
            # Decode
            data = jwt.decode(token, app.config.get("SECRET_KEY"))

            username = data.get("user")
            if not username:
                raise JwtTokenError(message="Username not found in token.")

            current_user = models.User.query.filter(models.User.username == username).first()
            project = data.get("project")
        except jwt.exceptions.InvalidTokenError as tokerr:
            raise JwtTokenDecodingError(message=str(tokerr))
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise DatabaseError(message=str(sqlerr))
        else:
            return f(current_user, project, *args, **kwargs)

    return validate_token


# PROJECTS ######################################################### PROJECTS #


def project_access_required(f):
    """Decorator function to verify the users access to the project."""

    @functools.wraps(f)
    def verify_project_access(current_user, project, *args, **kwargs):
        """Verifies that the user has been granted access to the project."""

        if not project.get("id"):
            raise MissingProjectIDError(message="Project ID not found.")

        if not project.get("verified"):
            raise IncorrectDecoratorUsageException(
                message=f"Access to project {project['id']} not yet verified. "
            )

        return f(current_user, project, *args, **kwargs)

    return verify_project_access


# S3 ##################################################################### S3 #


def connect_cloud(func):
    """Connect to S3"""

    @functools.wraps(func)
    def init_resource(self, *args, **kwargs):

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
