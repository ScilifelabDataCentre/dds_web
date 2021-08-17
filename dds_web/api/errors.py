from werkzeug import exceptions
import logging
import flask

general_logger = logging.getLogger("general")
action_logger = logging.getLogger("actions")

extra_info = {"result": "DENIED"}


class MissingCredentialsError(exceptions.HTTPException):
    def __init__(self, message="Missing username and/or password."):
        super().__init__(message)

        general_logger.info(message)


class ItemDeletionError(exceptions.HTTPException):
    pass


class DatabaseError(exceptions.HTTPException):
    def __init__(
        self, message="The DDS encountered an Flask-SQLAlchemy issue.", username=None, project=None
    ):
        super().__init__(message)

        general_logger.info(message)


class InvalidUserCredentialsError(exceptions.HTTPException):
    """Errors due to user authentication."""

    def __init__(self, message="Incorrect username and/or password!", username=None, project=None):
        super().__init__(message)

        general_logger.info(message)

        action_logger.warning(
            message,
            extra={
                **extra_info,
                "current_user": username,
                "action": "User authentication",
                "project": project,
            },
        )


class JwtTokenGenerationError(exceptions.HTTPException):
    pass


errors = {
    "ItemDeletionError": {"message": "Removal of item(s) from S3 bucket failed.", "status": 500},
    "MissingCredentialsError": {"status": 400},
    "DatabaseError": {"status": 500},
    "InvalidUserCredentialsError": {"status": 400},
    "JwtTokenGenerationError": {"status": 500},
}
