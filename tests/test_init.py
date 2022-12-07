from dds_web import fill_db_wrapper, create_new_unit, update_uploaded_file_with_log
import click.testing
import pytest
from dds_web import db
import dds_web
import dds_web.api.api_s3_connector
from dds_web.database import models
from unittest.mock import patch
import typing
from pyfakefs.fake_filesystem import FakeFilesystem
import os
from tests import DDSEndpoint, DEFAULT_HEADER, UserAuth, USER_CREDENTIALS
import http
import werkzeug
import flask
import flask_mail


@pytest.fixture
def runner() -> click.testing.CliRunner:
    return click.testing.CliRunner()


def mock_commit():
    return


# fill_db_wrapper


def test_fill_db_wrapper_production(client, runner) -> None:
    """Run init-db with the production argument."""
    result: click.testing.Result = runner.invoke(fill_db_wrapper, ["production"])
    assert result.exit_code == 1


def test_fill_db_wrapper_devsmall(client, runner) -> None:
    """Run init-db with the dev-small argument."""
    result: click.testing.Result = runner.invoke(fill_db_wrapper, ["dev-small"])
    assert result.exit_code == 1


# def test_fill_db_wrapper_devbig(client, runner) -> None:
#     """Run init-db with the dev-big argument."""
#     result: click.testing.Result = runner.invoke(fill_db_wrapper, ["dev-big"])
#     assert result.exit_code == 1


# create_new_unit


def create_command_options_from_dict(options: typing.Dict) -> typing.List:
    """Create a list with options and values from a dict."""
    # Create command options
    command_options: typing.List = []
    for key, val in options.items():
        command_options.append(f"--{key}")
        command_options.append(val)

    return command_options


correct_unit: typing.Dict = {
    "name": "newname",
    "public_id": "newpublicid",
    "external_display_name": "newexternaldisplay",
    "contact_email": "newcontact@mail.com",
    "internal_ref": "newinternalref",
    "safespring_endpoint": "newsafespringendpoint",
    "safespring_name": "newsafespringname",
    "safespring_access": "newsafespringaccess",
    "safespring_secret": "newsafespringsecret",
    "days_in_available": 45,
    "days_in_expired": 15,
}


def test_create_new_unit_public_id_too_long(client, runner) -> None:
    """Create new unit, public_id too long."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "public" * 10

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' can be a maximum of 50 characters" in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_incorrect_characters(client, runner) -> None:
    """Create new unit, public_id has invalid characters (here _)."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "new_public_id"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' can only contain letters, numbers, dots (.) and hyphens (-)." in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_starts_with_dot(client, runner) -> None:
    """Create new unit, public_id starts with invalid character (. or -)."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = ".newpublicid"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' must begin with a letter or number." in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )

    # Change public_id again
    incorrect_unit["public_id"] = "-newpublicid"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' must begin with a letter or number." in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_too_many_dots(client, runner) -> None:
    """Create new unit, public_id has invalid number of dots."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "new.public..id"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' should not contain more than two dots." in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_public_id_invalid_start(client, runner) -> None:
    """Create new unit, public_id starts with prefix."""
    # Change public_id
    incorrect_unit: typing.Dict = correct_unit.copy()
    incorrect_unit["public_id"] = "xn--newpublicid"

    # Get command options
    command_options = create_command_options_from_dict(options=incorrect_unit)

    # Run command
    result: click.testing.Result = runner.invoke(create_new_unit, command_options)
    # assert "The 'public_id' cannot begin with the 'xn--' prefix." in result.output
    assert (
        not db.session.query(models.Unit).filter(models.Unit.name == incorrect_unit["name"]).all()
    )


def test_create_new_unit_success(client, runner) -> None:
    """Create new unit, public_id starts with prefix."""
    # Get command options
    command_options = create_command_options_from_dict(options=correct_unit)

    with patch("dds_web.db.session.commit", mock_commit):
        # Run command
        result: click.testing.Result = runner.invoke(create_new_unit, command_options)
        # assert f"Unit '{correct_unit['name']}' created" in result.output


# Update uploaded file with log


def mock_no_project():
    return None


def test_update_uploaded_file_with_log_nonexisting_project(client, runner) -> None:
    """Add file info to non existing project."""
    # Create command options
    command_options: typing.List = [
        "--project",
        "projectdoesntexist",
        "--path-to-log-file",
        "somefile",
    ]

    # Run command
    assert db.session.query(models.Project).all()
    with patch("dds_web.database.models.Project.query.filter_by", mock_no_project):
        result: click.testing.Result = runner.invoke(update_uploaded_file_with_log, command_options)
        assert result.exit_code == 1


def test_update_uploaded_file_with_log_nonexisting_file(client, runner, fs: FakeFilesystem) -> None:
    """Attempt to read file which does not exist."""
    # Verify that fake file does not exist
    non_existent_log_file: str = "this_is_not_a_file.json"
    assert not os.path.exists(non_existent_log_file)

    # Create command options
    command_options: typing.List = [
        "--project",
        "projectdoesntexist",
        "--path-to-log-file",
        non_existent_log_file,
    ]

    # Run command
    result: click.testing.Result = runner.invoke(update_uploaded_file_with_log, command_options)
    assert result.exit_code == 1


# block_if_maintenance - should be blocked in init by before_request


def test_block_if_maintenance_active_encryptedtoken_blocked(
    client: flask.testing.FlaskClient,
) -> None:
    """Non-authenticated users should not be able to authenticate during maintenance.

    Exception: Super Admins.
    """
    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # Researcher, Unit Personnel, Unit Admin
    for user in ["researcher", "unituser", "unitadmin"]:
        with patch.object(flask_mail.Mail, "send") as mock_mail_send:
            response = client.get(
                DDSEndpoint.ENCRYPTED_TOKEN,
                auth=UserAuth(USER_CREDENTIALS[user]).as_tuple(),
                headers=DEFAULT_HEADER,
            )
            assert mock_mail_send.call_count == 0

        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_encryptedtoken_super_admin_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # Try encrypted token - "/user/encrypted_token"
    with patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.get(
            DDSEndpoint.ENCRYPTED_TOKEN,
            auth=UserAuth(USER_CREDENTIALS["superadmin"]).as_tuple(),
            headers=DEFAULT_HEADER,
        )
        assert mock_mail_send.call_count == 1
    assert response.status_code == http.HTTPStatus.OK


def test_block_if_maintenance_inactive_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """All should be allowed to authenticate with basic auth when maintenance not ongoing."""
    # Maintenance should be off
    maintenance: models.Maintenance = models.Maintenance.query.first()
    assert not maintenance.active

    # Try authenticating all
    for user in ["superadmin", "unitadmin", "unituser", "researcher"]:
        with patch.object(flask_mail.Mail, "send") as mock_mail_send:
            response = client.get(
                DDSEndpoint.ENCRYPTED_TOKEN,
                auth=UserAuth(USER_CREDENTIALS[user]).as_tuple(),
                headers=DEFAULT_HEADER,
            )
            assert mock_mail_send.call_count == 1
        assert response.status_code == http.HTTPStatus.OK


def test_block_if_maintenance_inactive_first_ok_second_blocked(
    client: flask.testing.FlaskClient,
) -> None:
    """Block second factor for all but Super Admins if maintenance started after basic auth."""
    # Maintenance should be off
    maintenance: models.Maintenance = models.Maintenance.query.first()
    assert not maintenance.active

    # All but Super Admin: Basic auth OK, second factor FAIL
    for user in ["unitadmin", "unituser", "researcher"]:
        # Maintenance not active during basic auth
        maintenance.active = False
        db.session.commit()

        # Perform basic auth
        basic_auth = UserAuth(USER_CREDENTIALS[user])
        hotp_value = basic_auth.fetch_hotp()
        partial_token = basic_auth.partial_token(client)

        # Maintenance active during 2fa
        maintenance.active = True
        db.session.commit()

        # Attempt 2fa
        response = client.get(
            DDSEndpoint.SECOND_FACTOR,
            headers=partial_token,
            json={"HOTP": hotp_value.decode()},
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE

    # Super Admin:
    # Maintenance not active during basic auth
    maintenance.active = False
    db.session.commit()

    # Perform basic auth
    basic_auth = UserAuth(USER_CREDENTIALS["superadmin"])
    hotp_value = basic_auth.fetch_hotp()
    partial_token = basic_auth.partial_token(client)

    # Maintenance active during 2fa
    maintenance.active = True
    db.session.commit()

    # Attempt 2fa
    response = client.get(
        DDSEndpoint.SECOND_FACTOR,
        headers=partial_token,
        json={"HOTP": hotp_value.decode()},
    )
    assert response.status_code == http.HTTPStatus.OK


def test_block_if_maintenance_active_none_approved_users(client: flask.testing.FlaskClient) -> None:
    """More requests to be blocked if maintenance is active."""
    # Get maintenance row
    maintenance: models.Maintenance = models.Maintenance.query.first()

    for user in ["researcher", "unituser", "unitadmin"]:
        maintenance.active = False
        db.session.commit()

        # Perform authentication
        user_auth = UserAuth(USER_CREDENTIALS[user])
        token = user_auth.token(client)

        maintenance.active = True
        db.session.commit()

        # S3info - "/s3/proj"
        response = client.get(
            DDSEndpoint.S3KEYS,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # NewFile - "/file/new"
        # post
        response = client.post(
            DDSEndpoint.FILE_NEW,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."
        # put
        response = client.put(
            DDSEndpoint.FILE_NEW,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # MatchFiles - "/file/match"
        response = client.get(
            DDSEndpoint.FILE_MATCH,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # ListFiles - "/files/list"
        response = client.get(
            DDSEndpoint.LIST_FILES,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # RemoveFile - "/file/rm"
        response = client.delete(
            DDSEndpoint.REMOVE_FILE,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # RemoveDir - "/file/rmdir"
        response = client.delete(
            DDSEndpoint.REMOVE_FOLDER,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # FileInfo - "/file/info"
        response = client.get(
            DDSEndpoint.FILE_INFO,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # FileInfoAll - "/file/all/info"
        response = client.get(
            DDSEndpoint.FILE_INFO_ALL,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # UpdateFile - "/file/update"
        response = client.put(
            DDSEndpoint.FILE_UPDATE,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # NewFile - "/file/new"
        response = client.post(
            DDSEndpoint.FILE_NEW,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # UserProjects - "/proj/list"
        response = client.get(
            DDSEndpoint.LIST_PROJ,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # RemoveContents - "/proj/rm"
        response = client.delete(
            DDSEndpoint.REMOVE_PROJ_CONT,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # GetPublic - "/proj/public"
        response = client.get(
            DDSEndpoint.PROJ_PUBLIC,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # GetPrivate - "/proj/private"
        response = client.get(
            DDSEndpoint.PROJ_PRIVATE,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # CreateProject - "/proj/create"
        response = client.post(
            DDSEndpoint.PROJECT_CREATE,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # ProjectUsers - "/proj/users"
        response = client.get(
            DDSEndpoint.LIST_PROJ_USERS,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # ProjectStatus - "/proj/status"
        # get
        response = client.get(
            DDSEndpoint.PROJECT_STATUS,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."
        # post
        response = client.post(
            DDSEndpoint.PROJECT_STATUS,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # ProjectAccess - "/proj/access"
        response = client.post(
            DDSEndpoint.PROJECT_ACCESS,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # ProjectBusy - "/proj/busy"
        response = client.put(
            DDSEndpoint.PROJECT_BUSY,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # ProjectInfo - "/proj/info"
        response = client.get(
            DDSEndpoint.PROJECT_INFO,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # RetrieveUserInfo - "/user/info"
        response = client.get(
            DDSEndpoint.USER_INFO,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # AddUser - "/user/add"
        response = client.post(
            DDSEndpoint.USER_ADD,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # DeleteUser - "/user/delete"
        response = client.delete(
            DDSEndpoint.USER_DELETE,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # DeleteUserSelf - "/file/new"
        response = client.delete(
            DDSEndpoint.USER_DELETE_SELF,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # RemoveUserAssociation - "/user/access/revoke"
        response = client.post(
            DDSEndpoint.REMOVE_USER_FROM_PROJ,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # UserActivation - "/user/activation"
        response = client.post(
            DDSEndpoint.USER_ACTIVATION,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # RequestHOTPActivation - "/user/hotp/activate"
        response = client.post(
            DDSEndpoint.HOTP_ACTIVATION,
            auth=user_auth.as_tuple(),
            headers=DEFAULT_HEADER,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # RequestTOTPActivation - "/user/totp/activate"
        response = client.post(
            DDSEndpoint.TOTP_ACTIVATION,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # Users - "/users"
        response = client.get(
            DDSEndpoint.LIST_USERS,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # InvitedUsers - "/user/invites"
        response = client.get(
            DDSEndpoint.LIST_INVITES,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # SetMaintenance - "/maintenance"
        response = client.put(
            DDSEndpoint.MAINTENANCE,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # AllUnits - "/unit/info/all"
        response = client.get(
            DDSEndpoint.LIST_UNITS_ALL,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # MOTD - "/motd"
        # get
        response = client.get(
            DDSEndpoint.MOTD,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.OK
        # post
        response = client.post(
            DDSEndpoint.MOTD,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # SendMOTD - "/motd/send"
        response = client.post(
            DDSEndpoint.MOTD_SEND,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # FindUser - "/user/find"
        response = client.get(
            DDSEndpoint.USER_FIND,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # ResetTwoFactor - "/user/totp/deactivate"
        response = client.put(
            DDSEndpoint.TOTP_DEACTIVATE,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # AnyProjectBusy - "/proj/busy/any"
        response = client.get(
            DDSEndpoint.PROJECT_BUSY_ANY,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."

        # ShowUsage - "/usage"
        response = client.get(
            DDSEndpoint.USAGE,
            headers=token,
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json and response.json.get("message") == "Maintenance of DDS is ongoing."


def test_block_if_maintenance_active_superadmin_ok(client: flask.testing.FlaskClient) -> None:
    """Super Admins should not be blocked during maintenance."""
    # Get maintenance row
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = False
    db.session.commit()

    # Perform authentication
    user_auth = UserAuth(USER_CREDENTIALS["superadmin"])
    token = user_auth.token(client)

    maintenance.active = True
    db.session.commit()

    # S3info - "/s3/proj"
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # NewFile - "/file/new"
    # post
    response = client.post(
        DDSEndpoint.FILE_NEW,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    # put
    response = client.put(
        DDSEndpoint.FILE_NEW,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # MatchFiles - "/file/match"
    response = client.get(
        DDSEndpoint.FILE_MATCH,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # ListFiles - "/files/list"
    response = client.get(
        DDSEndpoint.LIST_FILES,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # RemoveFile - "/file/rm"
    response = client.delete(
        DDSEndpoint.REMOVE_FILE,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # RemoveDir - "/file/rmdir"
    response = client.delete(
        DDSEndpoint.REMOVE_FOLDER,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # FileInfo - "/file/info"
    response = client.get(
        DDSEndpoint.FILE_INFO,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # FileInfoAll - "/file/all/info"
    response = client.get(
        DDSEndpoint.FILE_INFO_ALL,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # UpdateFile - "/file/update"
    response = client.put(
        DDSEndpoint.FILE_UPDATE,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # NewFile - "/file/new"
    response = client.post(
        DDSEndpoint.FILE_NEW,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # UserProjects - "/proj/list"
    response = client.get(
        DDSEndpoint.LIST_PROJ,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.OK

    # RemoveContents - "/proj/rm"
    response = client.delete(
        DDSEndpoint.REMOVE_PROJ_CONT,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # GetPublic - "/proj/public"
    response = client.get(
        DDSEndpoint.PROJ_PUBLIC,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # GetPrivate - "/proj/private"
    response = client.get(
        DDSEndpoint.PROJ_PRIVATE,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # CreateProject - "/proj/create"
    response = client.post(
        DDSEndpoint.PROJECT_CREATE,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # ProjectUsers - "/proj/users"
    response = client.get(
        DDSEndpoint.LIST_PROJ_USERS,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # ProjectStatus - "/proj/status"
    # get
    response = client.get(
        DDSEndpoint.PROJECT_STATUS,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    # post
    response = client.post(
        DDSEndpoint.PROJECT_STATUS,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # ProjectAccess - "/proj/access"
    response = client.post(
        DDSEndpoint.PROJECT_ACCESS,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # ProjectBusy - "/proj/busy"
    response = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # ProjectInfo - "/proj/info"
    response = client.get(
        DDSEndpoint.PROJECT_INFO,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # RetrieveUserInfo - "/user/info"
    response = client.get(
        DDSEndpoint.USER_INFO,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.OK

    # AddUser - "/user/add"
    response = client.post(
        DDSEndpoint.USER_ADD,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # DeleteUser - "/user/delete"
    response = client.delete(
        DDSEndpoint.USER_DELETE,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # DeleteUserSelf - "/file/new"
    response = client.delete(
        DDSEndpoint.USER_DELETE_SELF,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # RemoveUserAssociation - "/user/access/revoke"
    response = client.post(
        DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # UserActivation - "/user/activation"
    response = client.post(
        DDSEndpoint.USER_ACTIVATION,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # RequestHOTPActivation - "/user/hotp/activate"
    response = client.post(
        DDSEndpoint.HOTP_ACTIVATION,
        auth=user_auth.as_tuple(),
        headers=DEFAULT_HEADER,
    )
    assert response.status_code == http.HTTPStatus.OK

    # RequestTOTPActivation - "/user/totp/activate"
    response = client.post(
        DDSEndpoint.TOTP_ACTIVATION,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.OK

    # Users - "/users"
    response = client.get(
        DDSEndpoint.LIST_USERS,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.OK

    # InvitedUsers - "/user/invites"
    response = client.get(
        DDSEndpoint.LIST_INVITES,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.OK

    # SetMaintenance - "/maintenance"
    response = client.put(
        DDSEndpoint.MAINTENANCE,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # AllUnits - "/unit/info/all"
    response = client.get(
        DDSEndpoint.LIST_UNITS_ALL,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.OK

    # MOTD - "/motd"
    # get
    response = client.get(
        DDSEndpoint.MOTD,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.OK
    # post
    response = client.post(
        DDSEndpoint.MOTD,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # SendMOTD - "/motd/send"
    response = client.post(
        DDSEndpoint.MOTD_SEND,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # FindUser - "/user/find"
    response = client.get(
        DDSEndpoint.USER_FIND,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # ResetTwoFactor - "/user/totp/deactivate"
    response = client.put(
        DDSEndpoint.TOTP_DEACTIVATE,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # AnyProjectBusy - "/proj/busy/any"
    response = client.get(
        DDSEndpoint.PROJECT_BUSY_ANY,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.OK

    # ShowUsage - "/usage"
    response = client.get(
        DDSEndpoint.USAGE,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
