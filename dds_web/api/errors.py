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
from dds_web import auth

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


class KeyLengthError(SystemExit):
    """Invalid key length for encryption"""

    def __init__(self, encryption_key_char_length):
        message = (
            f"SECRET KEY MUST BE {encryption_key_char_length} "
            f"CHARACTERS LONG IN ORDER TO SATISFY THE CURRENT TOKEN ENCRYPTION!"
        )
        super().__init__(message)

        general_logger.error(message)


class AuthenticationError(exceptions.HTTPException):
    """Base class for errors due to authentication failure."""

    def __init__(self, message="Missing or incorrect credentials"):
        super().__init__(message)

        general_logger.warning(message)


class AccessDeniedError(exceptions.HTTPException):
    """Errors due to incorrect project permissions."""

    def __init__(
        self,
        project=None,
        username=None,
        message="The user does not have the necessary permissions.",
    ):
        super().__init__(message)

        if not username:
            username = auth.current_user()

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
        self,
        message,
        pass_message=False,
        project=None,
    ):

        general_logger.warning(message)

        action_logger.warning(
            message,
            extra={
                **extra_info,
                "current_user": auth.current_user(),
                "action": actions.get(flask.request.endpoint),
                "project": project,
            },
        )

        super().__init__(
            "The system encountered an error in the database." if not pass_message else message
        )


class EmptyProjectException(exceptions.HTTPException):
    """Something is attempted on an empty project."""

    def __init__(self, project, username=None, message="The project is empty."):
        super().__init__(message)

        general_logger.warning(message)

        if not username:
            username = auth.current_user()

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

    def __init__(self, project, message, pass_message=False):

        general_logger.warning(message)

        action_logger.warning(
            message,
            extra={
                **extra_info,
                "current_user": auth.current_user(),
                "action": actions.get(flask.request.endpoint),
                "project": project,
            },
        )

        super().__init__("Deletion of the file failed." if not pass_message else message)


class NoSuchProjectError(exceptions.HTTPException):
    """The project does not exist in the database"""

    def __init__(self, project, message="The specified project does not exist."):
        super().__init__(message)

        general_logger.warning(message)

        action_logger.warning(
            message,
            extra={
                **extra_info,
                "current_user": auth.current_user(),
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


class JwtTokenGenerationError(exceptions.HTTPException):
    """Errors when generating the JWT token during authentication."""

    def __init__(self, message="Error during JWT Token generation.", pass_message=False):

        general_logger.warning(message)

        super().__init__(
            "Unrecoverable error during the authentication process. Aborting."
            if not pass_message
            else message
        )


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


class KeyNotFoundError(exceptions.HTTPException):
    """Key not found in database."""

    def __init__(self, project, message="No key found for current project", pass_message=False):
        self.message = f"{message}: {project}"

        general_logger.warning(self.message)

        super().__init__("Unrecoverable key error. Aborting." if not pass_message else message)


class InviteError(exceptions.HTTPException):
    """Invite related errors."""

    def __init__(self, message="An error occurred during invite handling."):
        super().__init__(message)

        general_logger.warning(message)


class NoSuchUserError(Exception):
    """There is no such user found in the database."""

    def __init__(self, message="User not found."):
        super().__init__(message)

        general_logger.warning(message)


class NoSuchFileError(Exception):
    """There is no such file found in the database."""

    def __init__(self, message="Specified file does not exist."):
        super().__init__(message)

        general_logger.warning(message)


# ----------------------------------------------------------------------------------- #


# ----------------------------------------------------------------------------------- #


errors = {
    "ItemDeletionError": {
        "message": "Removal of item(s) from S3 bucket failed.",
        "status": http.HTTPStatus.INTERNAL_SERVER_ERROR,
    },
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
    "BucketNotFoundError": {"status": http.HTTPStatus.INTERNAL_SERVER_ERROR},
    "InviteError": {"status": http.HTTPStatus.BAD_REQUEST},
    "NoSuchUserError": {"status": http.HTTPStatus.BAD_REQUEST},
    "NoSuchFileError": {"status": http.HTTPStatus.BAD_REQUEST},
    "TooManyRequestsError": {
        "message": "Too many authentication requests in one hour",
        "status": http.HTTPStatus.TOO_MANY_REQUESTS,
    },
}
