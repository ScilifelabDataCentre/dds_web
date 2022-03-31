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
import json
import structlog

# Own modules
from dds_web import auth

####################################################################################################
# LOGGING ################################################################################ LOGGING #
####################################################################################################

general_logger = logging.getLogger("general")
action_logger = structlog.getLogger("actions")

extra_info = {"result": "DENIED"}


class LoggedHTTPException(exceptions.HTTPException):
    """Base class to enable standard action logging on HTTP Exceptions"""

    def __init__(self, message=None, **kwargs):
        # Put import here to avoid circular imports: errors -> utils -> models -> errors
        from dds_web.utils import get_username_or_request_ip

        with structlog.threadlocal.bound_threadlocal(
            message=message,
            resource=flask.request.path or "not applicable",
            project=flask.request.args.get("project") if flask.request.args else None,
            user=get_username_or_request_ip(),
        ):
            structlog.threadlocal.bind_threadlocal(response=f"{self.code.value} {self.code.phrase}")

            if kwargs:
                structlog.threadlocal.bind_threadlocal(extra=json.dumps(kwargs))

            action_logger.warning(f"exception.{self.__class__.__name__}")

            # make sure the threadlocal state is pruned after the log was written.
            structlog.threadlocal.clear_threadlocal()

            super().__init__(message)


####################################################################################################
# EXCEPTIONS ########################################################################## EXCEPTIONS #
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


class TokenMissingError(LoggedHTTPException):
    """Errors due to missing token."""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, message="Token is missing"):
        super().__init__(message)

        general_logger.warning(message)


class SensitiveContentMissingError(LoggedHTTPException):
    """Errors due to missing sensitive content in the encrypted token."""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, message="Sensitive content is missing in the encrypted token!"):
        super().__init__(message)

        general_logger.warning(message)


class KeySetupError(LoggedHTTPException):
    """Errors due to missing keys."""

    code = http.HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message="Keys are not properly setup!"):
        super().__init__(message)

        general_logger.warning(message)


class KeyOperationError(LoggedHTTPException):
    """Errors due to issues in key operations."""

    code = http.HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message="A key cannot be processed!"):
        super().__init__(message)

        general_logger.warning(message)


class AuthenticationError(LoggedHTTPException):
    """Base class for errors due to authentication failure."""

    code = http.HTTPStatus.UNAUTHORIZED

    def __init__(self, message="Missing or incorrect credentials"):
        super().__init__(message)

        general_logger.warning(message)


class AccessDeniedError(LoggedHTTPException):
    """Errors due to incorrect project permissions."""

    code = http.HTTPStatus.FORBIDDEN  # 403
    description = "You do not have the necessary permissions."

    def __init__(
        self,
        project=None,
        username=None,
        message=description,
    ):
        if username:
            structlog.threadlocal.bind_threadlocal(user=username)
        if project:
            structlog.threadlocal.bind_threadlocal(project=project)

        general_logger.warning(message)
        super().__init__(message)


class DatabaseError(LoggedHTTPException):
    """Baseclass for database related issues."""

    code = http.HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message,
        alt_message=None,
        pass_message=False,
        project=None,
    ):

        general_logger.error(message)

        if project:
            structlog.threadlocal.bind_threadlocal(project=project)

        super().__init__(
            (alt_message or "The system encountered an error in the database.")
            if not pass_message
            else message
        )


class EmptyProjectException(LoggedHTTPException):
    """Something is attempted on an empty project."""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, project, username=None, message="The project is empty."):

        if not username:
            username = auth.current_user()
        structlog.threadlocal.bind_threadlocal(user=username)
        if project:
            structlog.threadlocal.bind_threadlocal(project=project)

        general_logger.warning(message)
        super().__init__(message)


class DeletionError(LoggedHTTPException):
    """Deletion of item failed."""

    code = http.HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, project, message, alt_message=None, pass_message=False):

        if project:
            structlog.threadlocal.bind_threadlocal(project=project)

        general_logger.warning(message)
        super().__init__((alt_message or "Deletion failed.") if not pass_message else message)


class NoSuchProjectError(LoggedHTTPException):
    """The project does not exist in the database"""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, project, message="The specified project does not exist."):

        if project:
            structlog.threadlocal.bind_threadlocal(project=project)

        general_logger.warning(message)
        super().__init__(message)


class BucketNotFoundError(LoggedHTTPException):
    """No bucket name found in the database."""

    code = http.HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message="No bucket found for the specified project."):
        super().__init__(message)

        general_logger.warning(message)


class S3ProjectNotFoundError(LoggedHTTPException):
    """No Safespring project found in database or connection failed."""

    code = http.HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message="Safespring S3 project not found."):
        super().__init__(message)

        general_logger.warning(message)


class S3ConnectionError(LoggedHTTPException):
    """Error when attempting to connect or perform action with S3 connection."""

    code = http.HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message, alt_message=None, pass_message=False):
        super().__init__(message)

        general_logger.warning(
            (alt_message or "An error occurred when connecting to the S3 storage")
            if pass_message
            else message
        )


class S3InfoNotFoundError(LoggedHTTPException):
    """S3 info could not be found."""

    code = http.HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message):
        super().__init__(message)

        general_logger.warning(message)


class JwtTokenGenerationError(LoggedHTTPException):
    """Errors when generating the JWT token during authentication."""

    code = http.HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message="Error during JWT Token generation.", pass_message=False):

        general_logger.warning(message)

        super().__init__(
            "Unrecoverable error during the authentication process. Aborting."
            if not pass_message
            else message
        )


class MissingProjectIDError(LoggedHTTPException):
    """Errors due to missing project ID in request."""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, message="Project ID missing!"):
        super().__init__(message)

        general_logger.warning(message)


class DDSArgumentError(LoggedHTTPException):
    """Base class for errors occurring due to missing request arguments."""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, message):
        super().__init__(message)

        general_logger.warning(message)


class MissingJsonError(LoggedHTTPException):
    """Not enough data specified to the endpoint in the form of json."""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, message):
        super().__init__(message)

        general_logger.warning(message)


class MissingMethodError(LoggedHTTPException):
    """Raised when none of the following are found in a request: put, get, ls, rm."""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, message="No method found in request."):
        super().__init__(message)

        general_logger.warning(message)


class KeyNotFoundError(LoggedHTTPException):
    """Key not found in database."""

    code = http.HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, project, message="No key found for current project", pass_message=False):
        self.message = f"{message}: {project}"

        general_logger.warning(self.message)

        super().__init__("Unrecoverable key error. Aborting." if not pass_message else message)


class InviteError(LoggedHTTPException):
    """Invite related errors."""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, message="An error occurred during invite handling."):
        super().__init__(message)

        general_logger.warning(message)


class UserDeletionError(LoggedHTTPException):
    """Errors regarding deleting user accounts."""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, message="User deletion failed.", alt_message=None):

        general_logger.warning(message)
        super().__init__(alt_message or message)


class NoSuchUserError(LoggedHTTPException):
    """There is no such user found in the database."""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, message="User not found."):
        super().__init__(message)

        general_logger.warning(message)


class NoSuchFileError(LoggedHTTPException):
    """There is no such file found in the database."""

    code = http.HTTPStatus.BAD_REQUEST

    def __init__(self, message="Specified file does not exist."):
        super().__init__(message)

        general_logger.warning(message)


class TooManyRequestsError(LoggedHTTPException):

    code = http.HTTPStatus.TOO_MANY_REQUESTS
    description = "Too many authentication requests in one hour"

    def __init__(self):

        super().__init__(self.description)
        general_logger.warning(self.description)


class RoleException(LoggedHTTPException):

    code = http.HTTPStatus.FORBIDDEN

    def __init__(self, message="Invalid role."):

        super().__init__(message)
        general_logger.warning(message)
