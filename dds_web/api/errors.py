from werkzeug import exceptions
import logging
import flask
from dds_web import actions

general_logger = logging.getLogger("general")
action_logger = logging.getLogger("actions")

extra_info = {"result": "DENIED"}


class ItemDeletionError(exceptions.HTTPException):
    pass


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


class InvalidUserCredentialsError(exceptions.HTTPException):
    """Errors due to user authentication."""

    def __init__(self, message="Incorrect username and/or password.", username=None, project=None):
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


# ----------------------------------------------------------------------------------- #
class JwtTokenError(exceptions.HTTPException):
    """Base class for exceptions triggered when handling the JWT tokens."""

    def __init__(self, message):
        super().__init__(message)

        general_logger.warning(message)


class JwtTokenGenerationError(JwtTokenError):
    """Errors when generating the JWT token during authentication."""


class JwtTokenDecodingError(JwtTokenError):
    """Errors occuring when decoding the JWT token."""


class MissingProjectIDError(JwtTokenError):
    """Errors due to missing project ID in request."""

    def __init__(self, message="Attempting to validate users project access without project ID"):
        super().__init__(message)


# ----------------------------------------------------------------------------------- #
class DDSArgumentError(exceptions.HTTPException):
    """Base class for errors occurring due to missing request arguments."""

    def __init__(self, message):
        super().__init__(message)

        general_logger.warning(message)


class MissingCredentialsError(DDSArgumentError):
    """Raised when username and/or password arguments are missing from a request."""

    def __init__(self, message="Missing username and/or password."):
        super().__init__(message)


class MissingMethodError(DDSArgumentError):
    """Raised when none of the following are found in a request: put, get, ls, rm."""

    def __init__(self, message="No method found in request."):
        super().__init__(message)


class TokenNotFoundError(DDSArgumentError):
    """Missing token in request."""

    def __init__(self, message="JWT Token not found in HTTP header."):
        super().__init__(message)


errors = {
    "ItemDeletionError": {"message": "Removal of item(s) from S3 bucket failed.", "status": 500},
    "DatabaseError": {"status": 500},
    "InvalidUserCredentialsError": {"status": 400},
    "JwtTokenError": {"status": 500},
    "JwtTokenGenerationError": {"status": 500},
    "JwtTokenDecodingError": {"status": 500},
    "DDSArgumentError": {"status": 400},
    "MissingCredentialsError": {"status": 400},
    "MissingMethodError": {"status": 400},
    "TokenNotFoundError": {"status": 400},
}
