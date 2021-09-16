"""Custom exceptions for the DDS."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import logging

# Installed
from werkzeug import exceptions
import flask
import http

# Own modules
from dds_web import actions

####################################################################################################
# LOGGING ################################################################################ LOGGING #
####################################################################################################

general_logger = logging.getLogger("general")
action_logger = logging.getLogger("actions")

extra_info = {"result": "DENIED"}

####################################################################################################
# EXCEPTIONS ########################################################################## EXCEPTIONS #
####################################################################################################


class ItemDeletionError(exceptions.HTTPException):
    pass


####################################################################################################


class AuthenticationError(exceptions.HTTPException):
    """Base class for errors due to authentication failure."""

    def __init__(self, message="Missing or incorrect credentials"):
        super().__init__(message)

        general_logger.warning(message)


class AccessDeniedError(exceptions.HTTPException):
    """Errors due to incorrect project permissions."""

    def __init__(self, username, project, message="The user does not have the necessary permissions."):
        super().__init__(message)

        action_logger.warning(
            message,
            extra={
                **extra_info,
                "current_user": username,
                "action": actions.get(flask.request.endpoint),
                "project": project,
            },
        )


class DatabaseError(exceptions.HTTPException):
    """Baseclass for database related issues."""

    def __init__(
        self, message="The DDS encountered an Flask-SQLAlchemy issue.", username=None, project=None
    ):
        super().__init__(message)

        general_logger.warning(message)

        action_logger.warning(
            message,
            extra={
                **extra_info,
                "current_user": username,
                "action": actions.get(flask.request.endpoint),
                "project": project,
            },
        )


class EmptyProjectException(exceptions.HTTPException):
    """Something is attempted on an empty project."""

    def __init__(self, project, username=None, message="The project is empty."):
        super().__init__(message)

        general_logger.warning(message)

        action_logger.warning(
            message,
            extra={
                **extra_info,
                "current_user": username,
                "action": actions.get(flask.request.endpoint),
                "project": project,
            },
        )


class DeletionError(exceptions.HTTPException):
    """Deletion of item failed."""

    def __init__(self, username, project, message="Deletion failed."):
        super().__init__(message)

        general_logger.warning(message)

        action_logger.warning(
            message,
            extra={
                **extra_info,
                "current_user": username,
                "action": actions.get(flask.request.endpoint),
                "project": project,
            },
        )


class NoSuchProjectError(exceptions.HTTPException):
    """The project does not exist in the database"""

    def __init__(self, username, project, message="The specified project does not exist."):
        super().__init__(message)

        general_logger.warning(message)

        action_logger.warning(
            message,
            extra={
                **extra_info,
                "current_user": username,
                "action": actions.get(flask.request.endpoint),
                "project": project,
            },
        )


class BucketNotFoundError(exceptions.HTTPException):
    """No bucket name found in the database."""

    def __init__(self, message="No bucket found for the specified project."):
        super().__init__(message)

        general_logger.warning(message)


class S3ProjectNotFoundError(exceptions.HTTPException):
    """No Safespring project found in database or connection failed."""

    def __init__(self, message="Safespring S3 project not found."):
        super().__init__(message)

        general_logger.warning(message)


class S3ConnectionError(exceptions.HTTPException):
    """Error when attempting to connect or perform action with S3 connection."""

    def __init__(self, message):
        super().__init__(message)

        general_logger.warning(message)


class S3InfoNotFoundError(exceptions.HTTPException):
    """S3 info could not be found."""

    def __init__(self, message):
        super().__init__(message)

        general_logger.warning(message)


class KeyNotFoundError(exceptions.HTTPException):
    """S3 keys not found."""

    def __init__(self, message):
        super().__init__(message)

        general_logger.warning(message)


class JwtTokenGenerationError(exceptions.HTTPException):
    """Errors when generating the JWT token during authentication."""

    def __init__(self, message):
        super().__init__(message)

        general_logger.warning(message)


class MissingProjectIDError(exceptions.HTTPException):
    """Errors due to missing project ID in request."""

    def __init__(self, message="Attempting to validate users project access without project ID"):
        super().__init__(message)

        general_logger.warning(message)


class DDSArgumentError(exceptions.HTTPException):
    """Base class for errors occurring due to missing request arguments."""

    def __init__(self, message):
        super().__init__(message)

        general_logger.warning(message)


class MissingMethodError(exceptions.HTTPException):
    """Raised when none of the following are found in a request: put, get, ls, rm."""

    def __init__(self, message="No method found in request."):
        super().__init__(message)

        general_logger.warning(message)


class PublicKeyNotFoundError(exceptions.HTTPException):
    """Public key not found in database"""

    def __init__(self, project, message="No key found for current project"):
        self.message = f"{message}: {project}"
        super().__init__(self.message)

        general_logger.warning(self.message)


####################################################################################################


errors = {
    "ItemDeletionError": {"message": "Removal of item(s) from S3 bucket failed.",
                          "status": http.HTTPStatus.INTERNAL_SERVER_ERROR},
    "DatabaseError": {"status": http.HTTPStatus.INTERNAL_SERVER_ERROR},
    "NoSuchProjectError": {"status": http.HTTPStatus.BAD_REQUEST},
    "AuthenticationError": {"status": http.HTTPStatus.UNAUTHORIZED},
    "AccessDeniedError": {"status": http.HTTPStatus.FORBIDDEN},
    "JwtTokenGenerationError": {"status": http.HTTPStatus.INTERNAL_SERVER_ERROR},
    "MissingProjectIDError": {"status": http.HTTPStatus.BAD_REQUEST},
    "DDSArgumentError": {"status": http.HTTPStatus.BAD_REQUEST},
    "MissingMethodError": {"status": http.HTTPStatus.BAD_REQUEST},
    "EmptyProjectException": {"status": http.HTTPStatus.BAD_REQUEST},
    "DeletionError": {"status": http.HTTPStatus.INTERNAL_SERVER_ERROR},
    "S3ConnectionError": {"status": http.HTTPStatus.INTERNAL_SERVER_ERROR},
    "S3ProjectNotFoundError": {"status": http.HTTPStatus.INTERNAL_SERVER_ERROR},
    "S3InfoNotFoundError": {"status": http.HTTPStatus.INTERNAL_SERVER_ERROR},
    "KeyNotFoundError": {"status": http.HTTPStatus.INTERNAL_SERVER_ERROR},
    "PublicKeyNotFoundError": {"status": http.HTTPStatus.INTERNAL_SERVER_ERROR},
    "BucketNotFoundError": {"status": http.HTTPStatus.INTERNAL_SERVER_ERROR},
}
