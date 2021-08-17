from werkzeug import exceptions
import logging
import flask
from dds_web import actions

general_logger = logging.getLogger("general")
action_logger = logging.getLogger("actions")

extra_info = {"result": "DENIED"}


class ItemDeletionError(exceptions.HTTPException):
    pass


class MissingCredentialsError(exceptions.HTTPException):
    def __init__(self, message="Missing username and/or password."):
        super().__init__(message)

        general_logger.info(message)


class DatabaseError(exceptions.HTTPException):
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

    def __init__(self, message="Incorrect username and/or password!", username=None, project=None):
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


class JwtTokenGenerationError(exceptions.HTTPException):
    def __init__(self, message):
        super().__init__(message)

        general_logger.warning(message)


errors = {
    "ItemDeletionError": {"message": "Removal of item(s) from S3 bucket failed.", "status": 500},
    "MissingCredentialsError": {"status": 400},
    "DatabaseError": {"status": 500},
    "InvalidUserCredentialsError": {"status": 400},
    "JwtTokenGenerationError": {"status": 500},
}
