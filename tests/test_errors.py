from http.client import RemoteDisconnected
from dds_web import errors
from unittest import mock
from werkzeug import exceptions
from _pytest.capture import CaptureFixture
import logging
import pytest
import http
import flask


class LoggedHTTPExceptionTest(errors.LoggedHTTPException):

    code = http.HTTPStatus.INTERNAL_SERVER_ERROR


def test_LoggedHTTPException(client: flask.testing.FlaskClient) -> None:
    with pytest.raises(LoggedHTTPExceptionTest) as err:
        raise LoggedHTTPExceptionTest(message="Some message", test="test")
    assert "Some message" in str(err.value)


def test_KeyLengthError(client: flask.testing.FlaskClient) -> None:
    with pytest.raises(errors.KeyLengthError) as err:
        raise errors.KeyLengthError(encryption_key_char_length=10)
    assert (
        str(err.value)
        == "SECRET KEY MUST BE 10 CHARACTERS LONG IN ORDER TO SATISFY THE CURRENT TOKEN ENCRYPTION!"
    )


def test_TokenMissingError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "Token is missing"

    with pytest.raises(errors.TokenMissingError) as err1:
        raise errors.TokenMissingError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.TokenMissingError) as err2:
        raise errors.TokenMissingError
    assert str(err2.value) == f"{error_start}{original_error}"

    alternative_error = "Another message"
    with pytest.raises(errors.TokenMissingError) as err3:
        raise errors.TokenMissingError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_SensitiveContentMissingError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "Sensitive content is missing in the encrypted token!"

    with pytest.raises(errors.SensitiveContentMissingError) as err1:
        raise errors.SensitiveContentMissingError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.SensitiveContentMissingError) as err2:
        raise errors.SensitiveContentMissingError
    assert str(err2.value) == f"{error_start}{original_error}"

    alternative_error = "Another message"
    with pytest.raises(errors.SensitiveContentMissingError) as err3:
        raise errors.SensitiveContentMissingError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_KeySetupError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.INTERNAL_SERVER_ERROR} Internal Server Error: "
    original_error = "Keys are not properly setup!"

    with pytest.raises(errors.KeySetupError) as err1:
        raise errors.KeySetupError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.KeySetupError) as err2:
        raise errors.KeySetupError
    assert str(err2.value) == f"{error_start}{original_error}"

    alternative_error = "Another message"
    with pytest.raises(errors.KeySetupError) as err3:
        raise errors.KeySetupError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_KeyOperationError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.INTERNAL_SERVER_ERROR} Internal Server Error: "
    original_error = "A key cannot be processed!"

    with pytest.raises(errors.KeyOperationError) as err1:
        raise errors.KeyOperationError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.KeyOperationError) as err2:
        raise errors.KeyOperationError
    assert str(err2.value) == f"{error_start}{original_error}"

    alternative_error = "Another message"
    with pytest.raises(errors.KeyOperationError) as err3:
        raise errors.KeyOperationError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_AuthenticationError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.UNAUTHORIZED} Unauthorized: "
    original_error = "Missing or incorrect credentials"

    with pytest.raises(errors.AuthenticationError) as err1:
        raise errors.AuthenticationError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.AuthenticationError) as err2:
        raise errors.AuthenticationError
    assert str(err2.value) == f"{error_start}{original_error}"

    alternative_error = "Another message"
    with pytest.raises(errors.AuthenticationError) as err3:
        raise errors.AuthenticationError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_AccessDeniedError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.FORBIDDEN} Forbidden: "
    original_error = "You do not have the necessary permissions."

    with pytest.raises(errors.AccessDeniedError) as err1:
        raise errors.AccessDeniedError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.AccessDeniedError) as err2:
        raise errors.AccessDeniedError
    assert str(err2.value) == f"{error_start}{original_error}"

    alternative_error = "Another message"
    with pytest.raises(errors.AccessDeniedError) as err3:
        raise errors.AccessDeniedError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_DatabaseError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.INTERNAL_SERVER_ERROR} Internal Server Error: "
    first_error = "Some error message"
    alternative_error = "Another message"

    with pytest.raises(errors.DatabaseError) as err1:
        raise errors.DatabaseError(message=first_error)
    assert str(err1.value) == f"{error_start}The system encountered an error in the database."

    with pytest.raises(errors.DatabaseError) as err2:
        raise errors.DatabaseError(message=first_error, pass_message=True)
    assert str(err2.value) == f"{error_start}{first_error}"

    with pytest.raises(errors.DatabaseError) as err3:
        raise errors.DatabaseError(
            message=first_error, alt_message=alternative_error, pass_message=True
        )
    assert str(err3.value) == f"{error_start}{first_error}"

    with pytest.raises(errors.DatabaseError) as err4:
        raise errors.DatabaseError(message=first_error, alt_message=alternative_error)
    assert str(err4.value) == f"{error_start}{alternative_error}"

    with pytest.raises(errors.DatabaseError) as err5:
        raise errors.DatabaseError(message=first_error, project="project_id")
    assert str(err5.value) == f"{error_start}The system encountered an error in the database."


def test_EmptyProjectException(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "The project is empty."
    alternative_error = "Another message"
    project_id = "project_id"

    with pytest.raises(errors.EmptyProjectException) as err1:
        raise errors.EmptyProjectException(project=project_id)
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.EmptyProjectException) as err2:
        raise errors.EmptyProjectException(project=project_id, message=alternative_error)
    assert str(err2.value) == f"{error_start}{alternative_error}"


def test_DeletionError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.INTERNAL_SERVER_ERROR} Internal Server Error: "
    first_error = "Some error message"
    alternative_error = "Another message"
    project_id = "project_id"

    with pytest.raises(errors.DeletionError) as err1:
        raise errors.DeletionError(project=project_id, message=first_error)
    assert str(err1.value) == f"{error_start}Deletion failed."

    with pytest.raises(errors.DeletionError) as err2:
        raise errors.DeletionError(project=project_id, message=first_error, pass_message=True)
    assert str(err2.value) == f"{error_start}{first_error}"

    with pytest.raises(errors.DeletionError) as err3:
        raise errors.DeletionError(
            project=project_id,
            message=first_error,
            alt_message=alternative_error,
            pass_message=True,
        )
    assert str(err3.value) == f"{error_start}{first_error}"

    with pytest.raises(errors.DeletionError) as err4:
        raise errors.DeletionError(
            project=project_id, message=first_error, alt_message=alternative_error
        )
    assert str(err4.value) == f"{error_start}{alternative_error}"


def test_NoSuchProjectError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "The specified project does not exist."
    alternative_error = "Another message"
    project_id = "project_id"

    with pytest.raises(errors.NoSuchProjectError) as err1:
        raise errors.NoSuchProjectError(project=project_id)
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.NoSuchProjectError) as err2:
        raise errors.NoSuchProjectError(project=project_id, message=alternative_error)
    assert str(err2.value) == f"{error_start}{alternative_error}"


def test_BucketNotFoundError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.INTERNAL_SERVER_ERROR} Internal Server Error: "
    original_error = "No bucket found for the specified project."
    alternative_error = "Another message"

    with pytest.raises(errors.BucketNotFoundError) as err1:
        raise errors.BucketNotFoundError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.BucketNotFoundError) as err2:
        raise errors.BucketNotFoundError
    assert str(err2.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.BucketNotFoundError) as err3:
        raise errors.BucketNotFoundError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_S3ProjectNotFoundError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.INTERNAL_SERVER_ERROR} Internal Server Error: "
    original_error = "Safespring S3 project not found."
    alternative_error = "Another message"

    with pytest.raises(errors.S3ProjectNotFoundError) as err1:
        raise errors.S3ProjectNotFoundError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.S3ProjectNotFoundError) as err2:
        raise errors.S3ProjectNotFoundError
    assert str(err2.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.S3ProjectNotFoundError) as err3:
        raise errors.S3ProjectNotFoundError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_S3ConnectionError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.INTERNAL_SERVER_ERROR} Internal Server Error: "
    first_error = "Some error message"
    alternative_error = "Another message"

    with pytest.raises(errors.S3ConnectionError) as err1:
        raise errors.S3ConnectionError(message=first_error)
    assert str(err1.value) == f"{error_start}{first_error}"

    with pytest.raises(errors.S3ConnectionError) as err2:
        raise errors.S3ConnectionError(message=first_error, pass_message=True)
    assert str(err2.value) == f"{error_start}{first_error}"

    with pytest.raises(errors.S3ConnectionError) as err3:
        raise errors.S3ConnectionError(
            message=first_error, alt_message=alternative_error, pass_message=True
        )
    assert str(err3.value) == f"{error_start}{first_error}"

    with pytest.raises(errors.S3ConnectionError) as err4:
        raise errors.S3ConnectionError(message=first_error, alt_message=alternative_error)
    assert str(err4.value) == f"{error_start}{first_error}"


def test_S3InfoNotFoundError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.INTERNAL_SERVER_ERROR} Internal Server Error: "
    error_message = "Safespring S3 project not found."

    with pytest.raises(errors.S3InfoNotFoundError) as err1:
        raise errors.S3InfoNotFoundError(message=error_message)
    assert str(err1.value) == f"{error_start}{error_message}"


def test_JwtTokenGenerationError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.INTERNAL_SERVER_ERROR} Internal Server Error: "
    original_error = "Error during JWT Token generation."
    alternative_error = "Another message"

    with pytest.raises(errors.JwtTokenGenerationError) as err1:
        raise errors.JwtTokenGenerationError()
    assert (
        str(err1.value)
        == f"{error_start}Unrecoverable error during the authentication process. Aborting."
    )

    with pytest.raises(errors.JwtTokenGenerationError) as err2:
        raise errors.JwtTokenGenerationError(message=original_error)
    assert (
        str(err2.value)
        == f"{error_start}Unrecoverable error during the authentication process. Aborting."
    )

    with pytest.raises(errors.JwtTokenGenerationError) as err3:
        raise errors.JwtTokenGenerationError(message=alternative_error)
    assert (
        str(err3.value)
        == f"{error_start}Unrecoverable error during the authentication process. Aborting."
    )

    with pytest.raises(errors.JwtTokenGenerationError) as err4:
        raise errors.JwtTokenGenerationError(pass_message=True)
    assert str(err4.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.JwtTokenGenerationError) as err5:
        raise errors.JwtTokenGenerationError(message=alternative_error, pass_message=True)
    assert str(err5.value) == f"{error_start}{alternative_error}"


def test_MissingProjectIDError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "Project ID missing!"
    alternative_error = "Another message"

    with pytest.raises(errors.MissingProjectIDError) as err1:
        raise errors.MissingProjectIDError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.MissingProjectIDError) as err2:
        raise errors.MissingProjectIDError
    assert str(err2.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.MissingProjectIDError) as err3:
        raise errors.MissingProjectIDError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_DDSArgumentError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "Some message"

    with pytest.raises(errors.DDSArgumentError) as err1:
        raise errors.DDSArgumentError(message=original_error)
    assert str(err1.value) == f"{error_start}{original_error}"


def test_MissingJsonError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "Some message"

    with pytest.raises(errors.MissingJsonError) as err1:
        raise errors.MissingJsonError(message=original_error)
    assert str(err1.value) == f"{error_start}{original_error}"


def test_MissingMethodError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "No method found in request."
    alternative_error = "Another message"

    with pytest.raises(errors.MissingMethodError) as err1:
        raise errors.MissingMethodError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.MissingMethodError) as err2:
        raise errors.MissingMethodError
    assert str(err2.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.MissingMethodError) as err3:
        raise errors.MissingMethodError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_KeyNotFoundError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.INTERNAL_SERVER_ERROR} Internal Server Error: "
    first_error = "Some error message"
    alternative_error = "Another message"
    project_id = "project_id"

    with pytest.raises(errors.KeyNotFoundError) as err1:
        raise errors.KeyNotFoundError(project=project_id)
    assert str(err1.value) == f"{error_start}Unrecoverable key error. Aborting."

    with pytest.raises(errors.KeyNotFoundError) as err2:
        raise errors.KeyNotFoundError(project=project_id, message=first_error)
    assert str(err2.value) == f"{error_start}Unrecoverable key error. Aborting."

    with pytest.raises(errors.KeyNotFoundError) as err2:
        raise errors.KeyNotFoundError(project=project_id, message=first_error, pass_message=True)
    assert str(err2.value) == f"{error_start}{first_error}"


def test_InviteError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "An error occurred during invite handling."
    alternative_error = "Another message"

    with pytest.raises(errors.InviteError) as err1:
        raise errors.InviteError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.InviteError) as err2:
        raise errors.InviteError
    assert str(err2.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.InviteError) as err3:
        raise errors.InviteError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_UserDeletionError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "User deletion failed."
    alternative_error = "Another message"

    with pytest.raises(errors.UserDeletionError) as err1:
        raise errors.UserDeletionError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.UserDeletionError) as err2:
        raise errors.UserDeletionError
    assert str(err2.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.UserDeletionError) as err3:
        raise errors.UserDeletionError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"

    with pytest.raises(errors.UserDeletionError) as err4:
        raise errors.UserDeletionError(message=original_error, alt_message=alternative_error)
    assert str(err4.value) == f"{error_start}{alternative_error}"


def test_NoSuchUserError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "User not found."
    alternative_error = "Another message"

    with pytest.raises(errors.NoSuchUserError) as err1:
        raise errors.NoSuchUserError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.NoSuchUserError) as err2:
        raise errors.NoSuchUserError
    assert str(err2.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.NoSuchUserError) as err3:
        raise errors.NoSuchUserError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_NoSuchFileError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.BAD_REQUEST} Bad Request: "
    original_error = "Specified file does not exist."
    alternative_error = "Another message"

    with pytest.raises(errors.NoSuchFileError) as err1:
        raise errors.NoSuchFileError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.NoSuchFileError) as err2:
        raise errors.NoSuchFileError
    assert str(err2.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.NoSuchFileError) as err3:
        raise errors.NoSuchFileError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_TooManyRequestsError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.TOO_MANY_REQUESTS} Too Many Requests: "
    original_error = "Too many authentication requests in one hour"

    with pytest.raises(errors.TooManyRequestsError) as err1:
        raise errors.TooManyRequestsError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.TooManyRequestsError) as err2:
        raise errors.TooManyRequestsError
    assert str(err2.value) == f"{error_start}{original_error}"


def test_RoleException(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.FORBIDDEN} Forbidden: "
    original_error = "Invalid role."
    alternative_error = "Another message"

    with pytest.raises(errors.RoleException) as err1:
        raise errors.RoleException()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.RoleException) as err2:
        raise errors.RoleException
    assert str(err2.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.RoleException) as err3:
        raise errors.RoleException(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"


def test_VersionMismatchError(client: flask.testing.FlaskClient) -> None:
    error_start = f"{http.HTTPStatus.FORBIDDEN} Forbidden: "
    original_error = "You're using an old CLI version, please upgrade to the latest one."
    alternative_error = "Another message"

    with pytest.raises(errors.VersionMismatchError) as err1:
        raise errors.VersionMismatchError()
    assert str(err1.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.VersionMismatchError) as err2:
        raise errors.VersionMismatchError
    assert str(err2.value) == f"{error_start}{original_error}"

    with pytest.raises(errors.VersionMismatchError) as err3:
        raise errors.VersionMismatchError(message=alternative_error)
    assert str(err3.value) == f"{error_start}{alternative_error}"
