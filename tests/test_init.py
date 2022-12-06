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


def test_block_if_maintenance_active_encryptedtoken_researcher_blocked(
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
            auth=("researchuser", "password"),
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
            auth=("superadmin", "password"),
            headers=DEFAULT_HEADER,
        )
        assert mock_mail_send.call_count == 1
    assert response.status_code == http.HTTPStatus.OK

def test_block_if_maintenance_active_secondfactor_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Requests with wrong 2FA should be blocked if maintenance is active."""
    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # Try second factor - "/user/second_factor"
    response = client.get(
        DDSEndpoint.SECOND_FACTOR,
        headers={"Authorization": f"Bearer made.up.token.long.version", **DEFAULT_HEADER},
        json={"TOTP": "somrthing"},
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED


def test_block_if_maintenance_active_s3proj_not_approved(client: flask.testing.FlaskClient) -> None:
    """More requests to be blocked if maintenance is active."""
    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # Try s3info - "/s3/proj"
    response = client.get(
        DDSEndpoint.S3KEYS,
        headers=DEFAULT_HEADER,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_fileslist_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """More requests to be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["researchuser"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # Try list files - "/files/list"
    response = client.get(
        DDSEndpoint.LIST_FILES,
        headers=token,
        query_string={"project": "public_project_id"},
        json={"show_size": True},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_filematch_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """More requests to be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/file/match"
    response = client.get(
        DDSEndpoint.FILE_MATCH,
        headers=token,
        query_string={"project": "file_testing_project"},
        json=["non_existent_file"],
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_removefile_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # Try remove file - "/file/rm"
    from tests.test_files_new import FIRST_NEW_FILE

    response = client.delete(
        DDSEndpoint.REMOVE_FILE,
        headers=token,
        query_string={"project": "file_testing_project"},
        json=[FIRST_NEW_FILE["name"]],
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_removedir_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/file/rmdir"
    from tests.test_files_new import FIRST_NEW_FILE

    response = client.delete(
        DDSEndpoint.REMOVE_FOLDER,
        headers=token,
        query_string={"project": "file_testing_project"},
        json=[FIRST_NEW_FILE["subpath"]],
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_fileinfo_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["researchuser"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/file/info"
    with patch("dds_web.api.api_s3_connector.ApiS3Connector.generate_get_url") as mock_url:
        mock_url.return_value = "url"
        response = client.get(
            DDSEndpoint.FILE_INFO,
            headers=token,
            query_string={"project": "public_project_id"},
            json=["filename1"],
        )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_fileallinfo_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["researchuser"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/file/all/info"
    with patch("dds_web.api.api_s3_connector.ApiS3Connector.generate_get_url") as mock_url:
        mock_url.return_value = "url"
        response = client.get(
            DDSEndpoint.FILE_INFO_ALL,
            headers=token,
            query_string={"project": "public_project_id"},
        )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_projectlist_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/proj/list"
    response = client.get(
        DDSEndpoint.LIST_PROJ,
        headers=token,
        json={"usage": True},
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_removeprojectcontents_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/proj/rm"
    response = client.delete(
        DDSEndpoint.REMOVE_PROJ_CONT,
        headers=token,
        query_string={"project": "file_testing_project"},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_projectpublic_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/proj/public"
    response = client.get(
        DDSEndpoint.PROJ_PUBLIC, query_string={"project": "public_project_id"}, headers=token
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_projectprivate_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/proj/private"
    response = client.get(
        DDSEndpoint.PROJ_PRIVATE,
        query_string={"project": "public_project_id"},
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_createproject_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unituser"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/proj/create"
    from tests.test_project_creation import proj_data

    response = client.post(
        DDSEndpoint.PROJECT_CREATE,
        headers=token,
        json=proj_data,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_projectusers_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unituser"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/proj/users"
    response = client.get(
        DDSEndpoint.LIST_PROJ_USERS, query_string={"project": "public_project_id"}, headers=token
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_projectstatus_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/proj/status"
    response = client.post(
        DDSEndpoint.PROJECT_STATUS,
        headers=token,
        query_string={"project": "public_project_id"},
        json={"new_status": "Available"},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_projectaccess_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/proj/access"
    response = client.post(
        DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string={"project": "public_project_id"},
        json={"email": "unituser1@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_adduser_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/user/add"
    from tests.api.test_user import first_new_user

    response = client.post(
        DDSEndpoint.USER_ADD,
        headers=token,
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_deleteuser_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/user/delete"
    invited_user_row = models.Invite.query.first()
    response = client.delete(
        DDSEndpoint.USER_DELETE,
        headers=token,
        json={"email": invited_user_row.email, "is_invite": True},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_deleteself_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["delete_me_researcher"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/user/delete_self"
    with patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.delete(
            DDSEndpoint.USER_DELETE_SELF,
            headers=token,
            json=None,
        )
        # One email for partial token but no new for deletion confirmation
        assert mock_mail_send.call_count == 0
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_revokeaccess_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unituser"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/user/access/revoke"
    from tests.test_project_creation import proj_data_with_existing_users

    email = proj_data_with_existing_users["users_to_add"][0]["email"]
    response = client.post(
        DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=token,
        query_string={"project": "public_project_id"},
        json={"email": email},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_useractivation_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unitadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/user/activation"
    from tests.test_user_activation import unituser

    response = client.post(
        DDSEndpoint.USER_ACTIVATION,
        headers=token,
        json={**unituser, "action": "reactivate"},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_hotp_not_approved(client: flask.testing.FlaskClient) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["researcher"]).as_tuple()

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/user/hotp/activate"
    response = client.post(
        DDSEndpoint.HOTP_ACTIVATION,
        headers=DEFAULT_HEADER,
        auth=token,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_totp_not_approved(client: flask.testing.FlaskClient) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unituser"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/user/totp/activate"
    response = client.post(
        DDSEndpoint.TOTP_ACTIVATION,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_listusers_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["superadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/users"
    response = client.get(DDSEndpoint.LIST_USERS, headers=token)
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_finduser_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["superadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/user/find"
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.USER_FIND, headers=token, json={"username": models.User.query.first().username}
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_deactivatetotp_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["superadmin"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/user/totp/deactivate"
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.TOTP_DEACTIVATE,
        headers=token,
        json={"username": models.User.query.first().username},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_usage_not_approved(client: flask.testing.FlaskClient) -> None:
    """Certain endpoints should be blocked if maintenance is active."""
    # Auth before maintenance on
    token = UserAuth(USER_CREDENTIALS["unituser"]).token(client)

    # Get maintenance row and set to active
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # "/usage"
    response = client.get(
        DDSEndpoint.USAGE,
        headers=token,
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
