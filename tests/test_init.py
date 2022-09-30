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


def test_block_if_maintenance_active_encryptedtoken_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is not active."""
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


def test_block_if_maintenance_active_secondfactor_not_approved(
    client: flask.testing.FlaskClient,
) -> None:
    """Certain endpoints should be blocked if maintenance is not active."""
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
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_if_maintenance_active_s3proj_not_approved(client: flask.testing.FlaskClient) -> None:
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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
    """Certain endpoints should be blocked if maintenance is not active."""
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

# block data put


def test_block_put_if_maintenancen_not_active(client: flask.testing.FlaskClient) -> None:
    """Go through all endpoints that the upload command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # __get_s3_info
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.S3KEYS, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    expected_output: typing.Dict = {
        "safespring_project": user.unit.safespring_name,
        "url": user.unit.safespring_endpoint,
        "keys": {
            "access_key": user.unit.safespring_access,
            "secret_key": user.unit.safespring_secret,
        },
        "bucket": project.bucket,
    }
    for x, y in expected_output.items():
        assert x in response.json
        assert response.json[x] == y

    # __get_key (public)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PUBLIC, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify resposne
    public_key: str = response.json.get("public")
    assert public_key
    assert public_key == project.public_key.hex().upper()

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # check_previous_upload
    # - request
    files = models.File.query.filter_by(project_id=project.id).all()
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.FILE_MATCH,
        headers=token,
        query_string={"project": project.public_id},
        json=[f.name for f in files],
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    expected_output: typing.Dict = {file.name: file.name_in_bucket for file in files}
    returned_files: typing.Dict = response.json.get("files")
    assert returned_files
    for x, y in expected_output.items():
        assert x in returned_files
        assert returned_files[x] == y

    # add_file_db
    # - file info
    file_info = {
        "name": "newfile",
        "name_in_bucket": "new_file",
        "subpath": ".",
        "size": 0,
        "size_processed": 0,
        "compressed": False,
        "salt": "s" * 32,
        "public_key": "p" * 64,
        "checksum": "c" * 64,
    }
    # - request
    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.FILE_NEW,
        headers=token,
        query_string={"project": project.public_id},
        json=file_info,
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    message: str = response.json.get("message")
    assert message == f"File '{file_info['name']}' added to db."
    created_file: models.File = models.File.query.filter_by(
        name=file_info["name"],
        name_in_bucket=file_info["name_in_bucket"],
        subpath=file_info["subpath"],
        size_original=file_info["size"],
        size_stored=file_info["size_processed"],
        compressed=file_info["compressed"],
        salt=file_info["salt"],
        public_key=file_info["public_key"],
        checksum=file_info["checksum"],
    ).one_or_none()
    assert created_file

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_put_if_maintenancen_active_after_auth(client: flask.testing.FlaskClient) -> None:
    """Go through all endpoints that the upload command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # __get_s3_info
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.S3KEYS, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE

    # __get_key (public)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PUBLIC, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert not models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # check_previous_upload
    # - request
    files = models.File.query.filter_by(project_id=project.id).all()
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.FILE_MATCH,
        headers=token,
        query_string={"project": project.public_id},
        json=[f.name for f in files],
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE

    # add_file_db
    # - file info
    file_info = {
        "name": "newfile",
        "name_in_bucket": "new_file",
        "subpath": ".",
        "size": 0,
        "size_processed": 0,
        "compressed": False,
        "salt": "s" * 32,
        "public_key": "p" * 64,
        "checksum": "c" * 64,
    }
    # - request
    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.FILE_NEW,
        headers=token,
        query_string={"project": project.public_id},
        json=file_info,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    created_file: models.File = models.File.query.filter_by(
        name=file_info["name"],
        name_in_bucket=file_info["name_in_bucket"],
        subpath=file_info["subpath"],
        size_original=file_info["size"],
        size_stored=file_info["size_processed"],
        compressed=file_info["compressed"],
        salt=file_info["salt"],
        public_key=file_info["public_key"],
        checksum=file_info["checksum"],
    ).one_or_none()
    assert not created_file

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_block_put_if_maintenancen_active_after_busy(client: flask.testing.FlaskClient) -> None:
    """Go through all endpoints that the upload command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # __get_s3_info
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.S3KEYS, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    expected_output: typing.Dict = {
        "safespring_project": user.unit.safespring_name,
        "url": user.unit.safespring_endpoint,
        "keys": {
            "access_key": user.unit.safespring_access,
            "secret_key": user.unit.safespring_secret,
        },
        "bucket": project.bucket,
    }
    for x, y in expected_output.items():
        assert x in response.json
        assert response.json[x] == y

    # __get_key (public)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PUBLIC, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify resposne
    public_key: str = response.json.get("public")
    assert public_key
    assert public_key == project.public_key.hex().upper()

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # check_previous_upload
    # - request
    files = models.File.query.filter_by(project_id=project.id).all()
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.FILE_MATCH,
        headers=token,
        query_string={"project": project.public_id},
        json=[f.name for f in files],
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert response.json.get("message") == "Maintenance of DDS is ongoing."
    returned_files: typing.Dict = response.json.get("files")
    assert not returned_files

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_put_if_maintenancen_active_after_check_previous_upload(
    client: flask.testing.FlaskClient,
) -> None:
    """Go through all endpoints that the upload command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # __get_s3_info
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.S3KEYS, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    expected_output: typing.Dict = {
        "safespring_project": user.unit.safespring_name,
        "url": user.unit.safespring_endpoint,
        "keys": {
            "access_key": user.unit.safespring_access,
            "secret_key": user.unit.safespring_secret,
        },
        "bucket": project.bucket,
    }
    for x, y in expected_output.items():
        assert x in response.json
        assert response.json[x] == y

    # __get_key (public)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PUBLIC, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify resposne
    public_key: str = response.json.get("public")
    assert public_key
    assert public_key == project.public_key.hex().upper()

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # check_previous_upload
    # - request
    files = models.File.query.filter_by(project_id=project.id).all()
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.FILE_MATCH,
        headers=token,
        query_string={"project": project.public_id},
        json=[f.name for f in files],
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    expected_output: typing.Dict = {file.name: file.name_in_bucket for file in files}
    returned_files: typing.Dict = response.json.get("files")
    assert returned_files
    for x, y in expected_output.items():
        assert x in returned_files
        assert returned_files[x] == y

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # add_file_db
    # - file info
    file_info = {
        "name": "newfile",
        "name_in_bucket": "new_file",
        "subpath": ".",
        "size": 0,
        "size_processed": 0,
        "compressed": False,
        "salt": "s" * 32,
        "public_key": "p" * 64,
        "checksum": "c" * 64,
    }
    # - request
    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.FILE_NEW,
        headers=token,
        query_string={"project": project.public_id},
        json=file_info,
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    message: str = response.json.get("message")
    assert message == f"File '{file_info['name']}' added to db."
    created_file: models.File = models.File.query.filter_by(
        name=file_info["name"],
        name_in_bucket=file_info["name_in_bucket"],
        subpath=file_info["subpath"],
        size_original=file_info["size"],
        size_stored=file_info["size_processed"],
        compressed=file_info["compressed"],
        salt=file_info["salt"],
        public_key=file_info["public_key"],
        checksum=file_info["checksum"],
    ).one_or_none()
    assert created_file

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_put_if_maintenancen_active_after_add_file_db(
    client: flask.testing.FlaskClient,
) -> None:
    """Go through all endpoints that the upload command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # __get_s3_info
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.S3KEYS, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    expected_output: typing.Dict = {
        "safespring_project": user.unit.safespring_name,
        "url": user.unit.safespring_endpoint,
        "keys": {
            "access_key": user.unit.safespring_access,
            "secret_key": user.unit.safespring_secret,
        },
        "bucket": project.bucket,
    }
    for x, y in expected_output.items():
        assert x in response.json
        assert response.json[x] == y

    # __get_key (public)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PUBLIC, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify resposne
    public_key: str = response.json.get("public")
    assert public_key
    assert public_key == project.public_key.hex().upper()

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # check_previous_upload
    # - request
    files = models.File.query.filter_by(project_id=project.id).all()
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.FILE_MATCH,
        headers=token,
        query_string={"project": project.public_id},
        json=[f.name for f in files],
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    expected_output: typing.Dict = {file.name: file.name_in_bucket for file in files}
    returned_files: typing.Dict = response.json.get("files")
    assert returned_files
    for x, y in expected_output.items():
        assert x in returned_files
        assert returned_files[x] == y

    # add_file_db
    # - file info
    file_info = {
        "name": "newfile",
        "name_in_bucket": "new_file",
        "subpath": ".",
        "size": 0,
        "size_processed": 0,
        "compressed": False,
        "salt": "s" * 32,
        "public_key": "p" * 64,
        "checksum": "c" * 64,
    }
    # - request
    response: werkzeug.test.WrapperTestResponse = client.post(
        DDSEndpoint.FILE_NEW,
        headers=token,
        query_string={"project": project.public_id},
        json=file_info,
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    message: str = response.json.get("message")
    assert message == f"File '{file_info['name']}' added to db."
    created_file: models.File = models.File.query.filter_by(
        name=file_info["name"],
        name_in_bucket=file_info["name_in_bucket"],
        subpath=file_info["subpath"],
        size_original=file_info["size"],
        size_stored=file_info["size_processed"],
        compressed=file_info["compressed"],
        salt=file_info["salt"],
        public_key=file_info["public_key"],
        checksum=file_info["checksum"],
    ).one_or_none()
    assert created_file

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


# block data get


def test_block_get_if_maintenancen_not_active(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the download command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # __get_key (public)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PUBLIC, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify resposne
    public_key: str = response.json.get("public")
    assert public_key
    assert public_key == project.public_key.hex().upper()

    # __get_key (private)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PRIVATE, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert response.json.get("private")  # not testing encryption stuff here

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # __collect_file_info_remote
    # - request
    files = models.File.query.filter_by(project_id=project.id).all()
    with patch("dds_web.api.api_s3_connector.ApiS3Connector.generate_get_url") as mock_url:
        mock_url.return_value = "url"
        response: werkzeug.test.WrapperTestResponse = client.get(
            DDSEndpoint.FILE_INFO,
            headers=token,
            query_string={"project": project.public_id},
            json=[f.name for f in files],
        )
        assert response.status_code == http.HTTPStatus.OK

    # update_db
    # - file info
    file_to_update: models.File = files[0]
    assert file_to_update.time_latest_download is None
    file_info = {"name": file_to_update.name}
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.FILE_UPDATE,
        headers=token,
        query_string={"project": project.public_id},
        json=file_info,
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    message: str = response.json.get("message")
    assert message == "File info updated."
    updated_file: models.File = models.File.query.filter_by(
        name=file_to_update.name,
        name_in_bucket=file_to_update.name_in_bucket,
        subpath=file_to_update.subpath,
        size_original=file_to_update.size_original,
        size_stored=file_to_update.size_stored,
        compressed=file_to_update.compressed,
        salt=file_to_update.salt,
        public_key=file_to_update.public_key,
        checksum=file_to_update.checksum,
    ).one_or_none()
    assert updated_file and updated_file.time_latest_download is not None

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_get_if_maintenancen_active_after_auth(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the download command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # __get_key (public)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PUBLIC, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify resposne
    assert response.json.get("message") == "Maintenance of DDS is ongoing."

    # __get_key (private)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PRIVATE, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert response.json.get("message") == "Maintenance of DDS is ongoing."

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert response.json.get("message") == "Maintenance of DDS is ongoing."

    # __collect_file_info_remote
    # - request
    files = models.File.query.filter_by(project_id=project.id).all()
    with patch("dds_web.api.api_s3_connector.ApiS3Connector.generate_get_url") as mock_url:
        mock_url.return_value = "url"
        response: werkzeug.test.WrapperTestResponse = client.get(
            DDSEndpoint.FILE_INFO,
            headers=token,
            query_string={"project": project.public_id},
            json=[f.name for f in files],
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json.get("message") == "Maintenance of DDS is ongoing."

    # update_db
    # - file info
    file_to_update: models.File = files[0]
    assert file_to_update.time_latest_download is None
    file_info = {"name": file_to_update.name}
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.FILE_UPDATE,
        headers=token,
        query_string={"project": project.public_id},
        json=file_info,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert response.json.get("message") == "Maintenance of DDS is ongoing."

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert response.json.get("message") == "Maintenance of DDS is ongoing."


def test_block_get_if_maintenancen_active_after_busy(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the download command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # __get_key (public)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PUBLIC, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify resposne
    public_key: str = response.json.get("public")
    assert public_key
    assert public_key == project.public_key.hex().upper()

    # __get_key (private)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PRIVATE, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert response.json.get("private")  # not testing encryption stuff here

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # __collect_file_info_remote
    # - request
    files = models.File.query.filter_by(project_id=project.id).all()
    with patch("dds_web.api.api_s3_connector.ApiS3Connector.generate_get_url") as mock_url:
        mock_url.return_value = "url"
        response: werkzeug.test.WrapperTestResponse = client.get(
            DDSEndpoint.FILE_INFO,
            headers=token,
            query_string={"project": project.public_id},
            json=[f.name for f in files],
        )
        assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json.get("message") == "Maintenance of DDS is ongoing."

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_get_if_maintenancen_active_after_collect_file_info_remote(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the download command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # __get_key (public)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PUBLIC, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify resposne
    public_key: str = response.json.get("public")
    assert public_key
    assert public_key == project.public_key.hex().upper()

    # __get_key (private)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PRIVATE, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert response.json.get("private")  # not testing encryption stuff here

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # __collect_file_info_remote
    # - request
    files = models.File.query.filter_by(project_id=project.id).all()
    with patch("dds_web.api.api_s3_connector.ApiS3Connector.generate_get_url") as mock_url:
        mock_url.return_value = "url"
        response: werkzeug.test.WrapperTestResponse = client.get(
            DDSEndpoint.FILE_INFO,
            headers=token,
            query_string={"project": project.public_id},
            json=[f.name for f in files],
        )
        assert response.status_code == http.HTTPStatus.OK

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # update_db
    # - file info
    file_to_update: models.File = files[0]
    assert file_to_update.time_latest_download is None
    file_info = {"name": file_to_update.name}
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.FILE_UPDATE,
        headers=token,
        query_string={"project": project.public_id},
        json=file_info,
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    message: str = response.json.get("message")
    assert message == "File info updated."
    updated_file: models.File = models.File.query.filter_by(
        name=file_to_update.name,
        name_in_bucket=file_to_update.name_in_bucket,
        subpath=file_to_update.subpath,
        size_original=file_to_update.size_original,
        size_stored=file_to_update.size_stored,
        compressed=file_to_update.compressed,
        salt=file_to_update.salt,
        public_key=file_to_update.public_key,
        checksum=file_to_update.checksum,
    ).one_or_none()
    assert updated_file and updated_file.time_latest_download is not None

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_get_if_maintenancen_active_after_update_db(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the download command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # __get_key (public)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PUBLIC, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify resposne
    public_key: str = response.json.get("public")
    assert public_key
    assert public_key == project.public_key.hex().upper()

    # __get_key (private)
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(
        DDSEndpoint.PROJ_PRIVATE, headers=token, query_string={"project": project.public_id}
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert response.json.get("private")  # not testing encryption stuff here

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # __collect_file_info_remote
    # - request
    files = models.File.query.filter_by(project_id=project.id).all()
    with patch("dds_web.api.api_s3_connector.ApiS3Connector.generate_get_url") as mock_url:
        mock_url.return_value = "url"
        response: werkzeug.test.WrapperTestResponse = client.get(
            DDSEndpoint.FILE_INFO,
            headers=token,
            query_string={"project": project.public_id},
            json=[f.name for f in files],
        )
        assert response.status_code == http.HTTPStatus.OK

    # update_db
    # - file info
    file_to_update: models.File = files[0]
    assert file_to_update.time_latest_download is None
    file_info = {"name": file_to_update.name}
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.FILE_UPDATE,
        headers=token,
        query_string={"project": project.public_id},
        json=file_info,
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    message: str = response.json.get("message")
    assert message == "File info updated."
    updated_file: models.File = models.File.query.filter_by(
        name=file_to_update.name,
        name_in_bucket=file_to_update.name_in_bucket,
        subpath=file_to_update.subpath,
        size_original=file_to_update.size_original,
        size_stored=file_to_update.size_stored,
        compressed=file_to_update.compressed,
        salt=file_to_update.salt,
        public_key=file_to_update.public_key,
        checksum=file_to_update.checksum,
    ).one_or_none()
    assert updated_file and updated_file.time_latest_download is not None

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


# block data rm


def test_block_rm_all_if_maintenancen_not_active(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the remove command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # __collect_file_info_remote
    # - request
    response: werkzeug.test.WrapperTestResponse = client.delete(
        DDSEndpoint.REMOVE_PROJ_CONT,
        headers=token,
        query_string={"project": project.public_id},
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json.get("removed") is True

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_rm_all_if_maintenancen_after_auth(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the remove command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert response.json.get("message") == "Maintenance of DDS is ongoing."
    assert not models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # remove_all
    # - request
    response: werkzeug.test.WrapperTestResponse = client.delete(
        DDSEndpoint.REMOVE_PROJ_CONT,
        headers=token,
        query_string={"project": project.public_id},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json.get("message") == "Maintenance of DDS is ongoing."

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert response.json.get("message") == "Maintenance of DDS is ongoing."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_rm_all_if_maintenancen_active_after_busy(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the remove command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # remove_all
    # - request
    response: werkzeug.test.WrapperTestResponse = client.delete(
        DDSEndpoint.REMOVE_PROJ_CONT,
        headers=token,
        query_string={"project": project.public_id},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json.get("message") == "Maintenance of DDS is ongoing."

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_rm_all_if_maintenancen_active_after_rm(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the remove command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # remove_all
    # - request
    response: werkzeug.test.WrapperTestResponse = client.delete(
        DDSEndpoint.REMOVE_PROJ_CONT,
        headers=token,
        query_string={"project": project.public_id},
    )
    assert response.status_code == http.HTTPStatus.OK
    assert response.json.get("removed") is True
    assert models.File.query.filter_by(project_id=project.public_id).count() == 0

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_rm_file_if_maintenancen_after_auth(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the remove command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert response.json.get("message") == "Maintenance of DDS is ongoing."
    assert not models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # remove_file
    # - get files
    files: typing.List = [file.name for file in models.File.query.all()]
    # - request
    response: werkzeug.test.WrapperTestResponse = client.delete(
        DDSEndpoint.REMOVE_FILE,
        headers=token,
        query_string={"project": project.public_id},
        json=files,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json.get("message") == "Maintenance of DDS is ongoing."
    assert models.File.query.filter(models.File.name.in_(files)).count() == len(files)

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert response.json.get("message") == "Maintenance of DDS is ongoing."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_rm_file_if_maintenancen_active_after_busy(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the remove command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # remove_file
    # - get files
    files: typing.List = [file.name for file in models.File.query.all()]
    # - request
    response: werkzeug.test.WrapperTestResponse = client.delete(
        DDSEndpoint.REMOVE_FILE,
        headers=token,
        query_string={"project": project.public_id},
        json=files,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json.get("message") == "Maintenance of DDS is ongoing."
    assert models.File.query.filter(models.File.name.in_(files)).count() == len(files)

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_rm_file_if_maintenancen_active_after_rm(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the remove command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # remove_file
    # - get files
    files: typing.List = [file.name for file in models.File.query.all()]
    # - request
    response: werkzeug.test.WrapperTestResponse = client.delete(
        DDSEndpoint.REMOVE_FILE,
        headers=token,
        query_string={"project": project.public_id},
        json=files,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert not models.File.query.filter(models.File.name.in_(files)).all()

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_rm_folder_if_maintenancen_after_auth(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the remove command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert response.json.get("message") == "Maintenance of DDS is ongoing."
    assert not models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # remove_folder
    # - get folders
    files_in_folders: typing.List = models.File.query.filter(models.File.subpath != ".").all()
    folders: typing.List = list(set(file.subpath for file in files_in_folders))
    assert folders
    # - request
    response: werkzeug.test.WrapperTestResponse = client.delete(
        DDSEndpoint.REMOVE_FOLDER,
        headers=token,
        query_string={"project": project.public_id},
        json=folders,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json.get("message") == "Maintenance of DDS is ongoing."
    assert models.File.query.filter(models.File.subpath.in_(folders)).count() == len(
        files_in_folders
    )

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    # - verify response
    assert response.json.get("message") == "Maintenance of DDS is ongoing."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_rm_folder_if_maintenancen_active_after_busy(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the remove command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # remove_folder
    files_in_folders: typing.List = models.File.query.filter(models.File.subpath != ".").all()
    folders: typing.List = list(set(file.subpath for file in files_in_folders))
    assert folders
    # - request
    response: werkzeug.test.WrapperTestResponse = client.delete(
        DDSEndpoint.REMOVE_FOLDER,
        headers=token,
        query_string={"project": project.public_id},
        json=folders,
    )
    assert response.status_code == http.HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json.get("message") == "Maintenance of DDS is ongoing."
    assert models.File.query.filter(models.File.subpath.in_(folders)).count() == len(
        files_in_folders
    )

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()


def test_block_rm_folder_if_maintenancen_active_after_rm(
    client: flask.testing.FlaskClient, boto3_session
) -> None:
    """Go through all endpoints that the remove command uses.

    Check what happens when maintenance is set to active after upload started.
    """
    # Auth
    username: str = "unituser"
    token: typing.Dict = UserAuth(USER_CREDENTIALS[username]).token(client)
    project: models.Project = (
        models.User.query.filter_by(username="unituser").one_or_none().projects[0]
    )

    # list_all_active_motds
    # - new motd
    new_motd_message: str = "Test motd"
    new_motd: models.MOTD = models.MOTD(message=new_motd_message)
    db.session.add(new_motd)
    db.session.commit()
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.MOTD, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    assert isinstance(response.json.get("motds"), list)
    assert new_motd_message in response.json.get("motds")[0]["Message"]

    # get_user_name_if_logged_in
    # - request
    response: werkzeug.test.WrapperTestResponse = client.get(DDSEndpoint.USER_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    user: models.User = models.User.query.filter_by(username=username).one_or_none()
    expected_output: typing.Dict = {
        "email_primary": user.primary_email,
        "emails_all": [x.email for x in user.emails],
        "role": user.role,
        "username": username,
        "name": user.name,
    }
    info: typing.Dict = response.json.get("info")
    assert info
    for x, y in expected_output.items():
        assert x in info
        assert info[x] == y

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": True},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=True).one_or_none()

    # remove_folder
    # - get folders
    files_in_folders: typing.List = models.File.query.filter(models.File.subpath != ".").all()
    folders: typing.List = list(set(file.subpath for file in files_in_folders))
    assert folders
    # - request
    response: werkzeug.test.WrapperTestResponse = client.delete(
        DDSEndpoint.REMOVE_FOLDER,
        headers=token,
        query_string={"project": project.public_id},
        json=folders,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert not models.File.query.filter(models.File.subpath.in_(folders)).all()

    # Set maintenance to on
    maintenance: models.Maintenance = models.Maintenance.query.first()
    maintenance.active = True
    db.session.commit()

    # change_busy_status - busy
    # - request
    response: werkzeug.test.WrapperTestResponse = client.put(
        DDSEndpoint.PROJECT_BUSY,
        headers=token,
        query_string={"project": project.public_id},
        json={"busy": False},
    )
    assert response.status_code == http.HTTPStatus.OK
    # - verify response
    busy_status_set: bool = response.json.get("ok")
    assert busy_status_set
    message: str = response.json.get("message")
    assert message == f"Project {project.public_id} was set to not busy."
    assert models.Project.query.filter_by(public_id=project.public_id, busy=False).one_or_none()
