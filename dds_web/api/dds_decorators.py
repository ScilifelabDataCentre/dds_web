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

# Own modules
from dds_web import app
from dds_web.database import models
from dds_web.api.errors import MissingCredentialsError
from dds_web import actions

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################

# LOGGING ########################################################## LOGGING #


# AUTH ################################################################# AUTH #


def token_required(f):
    """Decorator function for verifying the JWT tokens in requests."""

    @functools.wraps(f)
    def validate_token(*args, **kwargs):
        token = None

        # Get the token from the header
        if "x-access-token" in flask.request.headers:
            token = flask.request.headers["x-access-token"]
            app.logger.debug(f"token recieved: {token}")
        # Deny access if token is missing
        if token is None or not token:
            return flask.make_response("Token is missing!", 401)

        # Verify the token
        try:
            # Decode
            data = jwt.decode(token, app.config["SECRET_KEY"])

            # NEW
            current_user = models.User.query.filter(models.User.username == data["user"]).first()
            project = data["project"]
        except Exception as err:
            app.logger.exception(err)
            return flask.make_response("Token is invalid!", 401)
        else:
            return f(current_user, project, *args, **kwargs)

    return validate_token


# PROJECTS ######################################################### PROJECTS #


def project_access_required(f):
    """Decorator function to verify the users access to the project."""

    @functools.wraps(f)
    def verify_project_access(current_user, project, *args, **kwargs):
        """Verifies that the user has been granted access to the project."""

        if project["id"] is None:
            return flask.make_response("Project ID missing. Cannot proceed", 401)

        if not project["verified"]:
            return flask.make_response(
                f"Access to project {project['id']} not yet verified. " "Checkout token settings.",
                401,
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
            return (
                False,
                f"Project does not yet have a " f"dedicated bucket in the S3 instance: {err}",
            )

        return func(self, *args, **kwargs)

    return check_bucket_exists
