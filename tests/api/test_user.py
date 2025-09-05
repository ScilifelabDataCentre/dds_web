from datetime import datetime
from datetime import timedelta
import typing
from unittest import mock
import dds_web
import flask_mail
import http
import json
import sqlalchemy
from dds_web import db
from dds_web.database import models
from dds_web.utils import current_time
import tests
import unittest
import werkzeug
import time

# CONFIG ################################################################################## CONFIG #

existing_project = "public_project_id"
existing_project_2 = "second_public_project_id"
first_new_email = {"email": "first_test_email@mailtrap.io"}
first_new_user = {**first_new_email, "role": "Researcher"}
first_new_owner = {**first_new_email, "role": "Project Owner"}
first_new_user_unit_admin = {**first_new_email, "role": "Unit Admin"}
first_new_user_unit_personel = {**first_new_email, "role": "Unit Personnel"}
first_new_user_existing_project = {**first_new_user, "project": "public_project_id"}
first_new_user_extra_args = {**first_new_user, "extra": "test"}
first_new_user_invalid_role = {**first_new_email, "role": "Invalid Role"}
first_new_user_invalid_email = {"email": "first_invalid_email", "role": first_new_user["role"]}
existing_invite = {"email": "existing_invite_email@mailtrap.io", "role": "Researcher"}
new_unit_admin = {"email": "new_unit_admin@mailtrap.io", "role": "Unit Admin"}
new_super_admin = {"email": "new_super_admin@mailtrap.io", "role": "Super Admin"}
new_unit_user = {"email": "new_unit_user@mailtrap.io", "role": "Unit Personnel"}
new_owner_existing_project = {
    "email": "new_owner@mailtrap.io",
    "project": "public_project_id",
    "role": "Project Owner",
}
existing_research_user = {"email": "researchuser2@mailtrap.io", "role": "Researcher"}
existing_research_user_owner = {"email": "researchuser2@mailtrap.io", "role": "Project Owner"}
existing_research_user_to_existing_project = {
    **existing_research_user,
    "project": "public_project_id",
}
existing_research_user_to_nonexistent_proj = {
    **existing_research_user,
    "project": "not_a_project_id",
}
change_owner_existing_user = {
    "email": "researchuser@mailtrap.io",
    "role": "Project Owner",
    "project": "public_project_id",
}
submit_with_same_ownership = {
    **existing_research_user_owner,
    "project": "second_public_project_id",
}
remove_user_project_owner = {"email": "projectowner@mailtrap.io"}
remove_user_unit_user = {"email": "unituser2@mailtrap.io"}
remove_user_project_owner = {"email": "projectowner@mailtrap.io"}

# UTILITY FUNCTIONS ############################################################ UTILITY FUNCTIONS #


def get_existing_projects():
    """Return existing projects for the tests"""
    existing_project_1 = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    existing_project_2 = models.Project.query.filter_by(
        public_id="second_public_project_id"
    ).one_or_none()

    return existing_project_1, existing_project_2


def invite_to_project(project, client, json_query):
    """Create a invitation of a user for a project"""
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project.public_id},
        json=json_query,
    )
    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=json_query["email"]).one_or_none()
    assert invited_user

    project_invite_keys = models.ProjectInviteKeys.query.filter_by(
        invite_id=invited_user.id, project_id=project.id
    ).one_or_none()
    assert project_invite_keys

    return invited_user


# AddUser ################################################################# AddUser #


def test_add_user_with_researcher(client):
    """Researchers cannot invite other users."""
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user is None


def test_add_user_with_unituser_no_role(client):
    """An ok invite requires a role to be specified."""
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=first_new_email,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    invited_user = models.Invite.query.filter_by(email=first_new_email["email"]).one_or_none()
    assert invited_user is None


def test_add_user_with_unitadmin_with_extraargs(client):
    """Extra args should not be noticed when inviting users."""
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=first_new_user_extra_args,
    )
    assert response.status_code == http.HTTPStatus.OK
    invited_user = models.Invite.query.filter_by(
        email=first_new_user_extra_args["email"]
    ).one_or_none()
    assert invited_user


def test_add_user_with_unitadmin_and_invalid_role(client):
    """An invalid role should result in a failed invite."""
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=first_new_user_invalid_role,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    invited_user = models.Invite.query.filter_by(
        email=first_new_user_invalid_role["email"]
    ).one_or_none()
    assert invited_user is None


def test_add_user_with_unitadmin_and_invalid_email(client):
    """An invalid email should not be accepted."""
    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
            json=first_new_user_invalid_email,
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        # An email is always sent when receiving the partial token
        mock_mail_send.assert_called_once()

    invited_user = models.Invite.query.filter_by(
        email=first_new_user_invalid_email["email"]
    ).one_or_none()
    assert invited_user is None


def test_add_user_with_unitadmin(client):
    """Add researcher as unit admin."""
    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=token,
            json=first_new_user,
        )
        # One mail sent for partial token and one for the invite
        assert mock_mail_send.call_count == 2

    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user
    assert invited_user.email == first_new_user["email"]
    assert invited_user.role == first_new_user["role"]

    assert invited_user.nonce is not None
    assert invited_user.public_key is not None
    assert invited_user.private_key is not None
    assert invited_user.project_invite_keys == []

    # Repeating the invite should not send a new invite:
    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=token,
            json=first_new_user,
        )
        # No new mail should be sent for the token and neither for an invite
        assert mock_mail_send.call_count == 0
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    message = response.json.get("message")
    assert "user was already added to the system" in message


def test_add_unit_user_with_unitadmin(client):
    """Add unit user as unit admin."""
    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=token,
            json=new_unit_user,
        )
        # One mail sent for partial token and one for the invite
        assert mock_mail_send.call_count == 2

    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=new_unit_user["email"]).one_or_none()
    assert invited_user
    assert invited_user.email == new_unit_user["email"]
    assert invited_user.role == new_unit_user["role"]

    assert invited_user.nonce is not None
    assert invited_user.public_key is not None
    assert invited_user.private_key is not None

    project_invite_keys = invited_user.project_invite_keys
    number_of_asserted_projects = 0
    for project_invite_key in project_invite_keys:
        if (
            project_invite_key.project.public_id == "public_project_id"
            or project_invite_key.project.public_id == "unused_project_id"
            or project_invite_key.project.public_id == "restricted_project_id"
            or project_invite_key.project.public_id == "second_public_project_id"
            or project_invite_key.project.public_id == "file_testing_project"
        ):
            number_of_asserted_projects += 1
    assert len(project_invite_keys) == number_of_asserted_projects
    assert len(project_invite_keys) == len(invited_user.unit.projects)
    assert len(project_invite_keys) == 5

    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=token,
            json=new_unit_user,
        )
        # No new mail should be sent for the token and neither for an invite
        assert mock_mail_send.call_count == 0

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    message = response.json.get("message")
    assert "user was already added to the system" in message


def test_add_user_with_superadmin(client):
    """Adding users as super admin should work."""
    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        token = tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client)
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=token,
            json=first_new_user,
        )
        # One mail sent for partial token and one for the invite
        assert mock_mail_send.call_count == 2

    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user
    assert invited_user.email == first_new_user["email"]
    assert invited_user.role == first_new_user["role"]

    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=token,
            json=first_new_user,
        )
        # No new mail should be sent for the token and neither for an invite
        assert mock_mail_send.call_count == 0

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    message = response.json.get("message")
    assert "user was already added to the system" in message


def test_add_user_existing_email_no_project(client):
    """Granting an existing user access to a project requires a project id."""
    invited_user = models.Invite.query.filter_by(
        email=existing_invite["email"], role=existing_invite["role"]
    ).one_or_none()
    assert invited_user
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=existing_invite,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST


def test_add_unitadmin_user_with_unitpersonnel_permission_denied(client):
    """Unit admins cannot be invited as unit personnel."""
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=new_unit_admin,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    invited_user = models.Invite.query.filter_by(email=new_unit_admin["email"]).one_or_none()
    assert invited_user is None


def test_invite_user_expired_not_deleted(client):
    """If an invite has expired and hasn't been removed from the database, the invite should be replaced"""

    # invite a new user
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    # Set the creation date in the DB to -7 days for now
    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    invited_user.created_at -= timedelta(hours=168)
    old_time = invited_user.created_at
    db.session.commit()

    # Send the invite again and confirm it works
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user

    # check that the date has been updated
    assert invited_user.created_at != old_time


def test_invite_user_existing_project_invite_expired(client):
    """If an invite to a project has expired and hasn't been removed, a new invite should replace the old one"""

    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()

    # invite a new user
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project.public_id},
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user

    # check row was added to project invite keys table
    project_invite_keys = models.ProjectInviteKeys.query.filter_by(
        invite_id=invited_user.id, project_id=project.id
    ).one_or_none()
    assert project_invite_keys

    # Set the creation date in the DB to -7 days for now
    invited_user.created_at -= timedelta(hours=168)
    old_time = invited_user.created_at
    db.session.commit()

    # Send the invite again and confirm it works
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project.public_id},
        json=first_new_user,
    )

    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user

    # check that the date has been updated
    assert invited_user.created_at != old_time

    # check that the project invite keys has a new row
    project_invite_keys_new = models.ProjectInviteKeys.query.filter_by(
        invite_id=invited_user.id, project_id=project.id
    ).one_or_none()
    assert project_invite_keys_new != project_invite_keys


def test_invite_user_expired_sqlalchemyerror(client):
    """Error message should be returned if sqlalchemyerror occurs during deletion of unanswered invite."""

    # Invite a new user
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    # Set the creation date in the DB to -7 days for now
    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    invited_user.created_at -= timedelta(hours=168)
    old_time = invited_user.created_at
    old_id = invited_user.id
    db.session.commit()

    from tests.api.test_project import mock_sqlalchemyerror

    # Simulate database error while trying to send new invite
    with unittest.mock.patch("dds_web.db.session.delete", mock_sqlalchemyerror):
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
            json=first_new_user,
        )
        assert response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert (
            response.json.get("message")
            == "Something happened while checking for existing account / active invite."
        )

    # Get invite again
    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user

    # The invite should be the same
    assert invited_user.created_at == old_time
    assert invited_user.id == old_id


# -- Add existing users to projects ################################# Add existing users to projects #
def test_add_existing_user_without_project(client):
    """Project required if inviting user to project."""
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=existing_research_user,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST


def test_research_user_cannot_add_existing_user_to_existing_project(client):
    """Research user cannot add other users to project."""
    user_copy = existing_research_user_to_existing_project.copy()
    project_id = user_copy.pop("project")

    project = models.Project.query.filter_by(public_id=project_id).one_or_none()
    user = models.Email.query.filter_by(
        email=existing_research_user_to_existing_project["email"]
    ).one_or_none()
    project_user_before_addition = models.ProjectUsers.query.filter(
        sqlalchemy.and_(
            models.ProjectUsers.user_id == user.user_id,
            models.ProjectUsers.project_id == project.id,
        )
    ).one_or_none()
    assert project_user_before_addition is None

    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": project_id},
        json=user_copy,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    project_user_after_addition = models.ProjectUsers.query.filter(
        sqlalchemy.and_(
            models.ProjectUsers.user_id == user.user_id,
            models.ProjectUsers.project_id == project.id,
        )
    ).one_or_none()
    assert project_user_after_addition is None


# projectowner adds researchuser2 to projects[0]
def test_project_owner_can_add_existing_user_to_existing_project(client):
    """Project owners can add users to existing projects."""
    user_copy = existing_research_user_to_existing_project.copy()
    project_id = user_copy.pop("project")

    project = models.Project.query.filter_by(public_id=project_id).one_or_none()
    user = models.Email.query.filter_by(
        email=existing_research_user_to_existing_project["email"]
    ).one_or_none()
    project_user_before_addition = models.ProjectUsers.query.filter(
        sqlalchemy.and_(
            models.ProjectUsers.user_id == user.user_id,
            models.ProjectUsers.project_id == project.id,
        )
    ).one_or_none()
    assert project_user_before_addition is None

    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client),
        query_string={"project": project_id},
        json=user_copy,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_user_after_addition = models.ProjectUsers.query.filter(
        sqlalchemy.and_(
            models.ProjectUsers.user_id == user.user_id,
            models.ProjectUsers.project_id == project.id,
        )
    ).one_or_none()
    assert project_user_after_addition is not None


def test_add_existing_user_to_existing_project(client):
    """Unit user can invite users to project."""
    user_copy = existing_research_user_to_existing_project.copy()
    project_id = user_copy.pop("project")

    project = models.Project.query.filter_by(public_id=project_id).one_or_none()
    user = models.Email.query.filter_by(
        email=existing_research_user_to_existing_project["email"]
    ).one_or_none()
    project_user_before_addition = models.ProjectUsers.query.filter(
        sqlalchemy.and_(
            models.ProjectUsers.user_id == user.user_id,
            models.ProjectUsers.project_id == project.id,
        )
    ).one_or_none()
    assert project_user_before_addition is None

    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project_id},
        json=user_copy,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_user_after_addition = models.ProjectUsers.query.filter(
        sqlalchemy.and_(
            models.ProjectUsers.user_id == user.user_id,
            models.ProjectUsers.project_id == project.id,
        )
    ).one_or_none()
    assert project_user_after_addition


def test_add_existing_user_to_existing_project_no_mail_flag(client):
    "Test that an e-mail notification is not send when the --no-mail flag is used"

    user_copy = existing_research_user_to_existing_project.copy()
    project_id = user_copy.pop("project")
    new_status = {"new_status": "Available"}
    user_copy["send_email"] = False
    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)

    # make project available prior to test, otherwise an e-mail is never sent.
    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=token,
        query_string={"project": project_id},
        data=json.dumps(new_status),
        content_type="application/json",
    )

    # Test mail sending is suppressed

    with unittest.mock.patch.object(flask_mail.Mail, "send") as mock_mail_send:
        with unittest.mock.patch.object(
            dds_web.api.user.AddUser, "compose_and_send_email_to_user"
        ) as mock_mail_func:
            print(user_copy)
            response = client.post(
                tests.DDSEndpoint.USER_ADD,
                headers=token,
                query_string={"project": project_id},
                data=json.dumps(user_copy),
                content_type="application/json",
            )
            # assert that no mail is being sent.
            assert mock_mail_func.called == False
    assert mock_mail_send.call_count == 0

    assert response.status_code == http.HTTPStatus.OK
    assert "An e-mail notification has not been sent." in response.json["message"]


def test_add_existing_user_to_existing_project_after_release(client):
    """User should be able to be added after project status release."""
    user_copy = existing_research_user_to_existing_project.copy()
    project_id = user_copy.pop("project")

    project = models.Project.query.filter_by(public_id=project_id).one_or_none()
    user = models.Email.query.filter_by(
        email=existing_research_user_to_existing_project["email"]
    ).one_or_none()
    project_user_before_addition = models.ProjectUsers.query.filter(
        sqlalchemy.and_(
            models.ProjectUsers.user_id == user.user_id,
            models.ProjectUsers.project_id == project.id,
        )
    ).one_or_none()
    assert project_user_before_addition is None

    # release project
    response = client.post(
        tests.DDSEndpoint.PROJECT_STATUS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project_id},
        json={"new_status": "Available"},
    )
    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"

    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project_id},
        json=user_copy,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_user_after_addition = models.ProjectUsers.query.filter(
        sqlalchemy.and_(
            models.ProjectUsers.user_id == user.user_id,
            models.ProjectUsers.project_id == project.id,
        )
    ).one_or_none()
    assert project_user_after_addition


def test_add_existing_user_to_nonexistent_proj(client):
    """Adding user to non existent project should fail."""
    user_copy = existing_research_user_to_nonexistent_proj.copy()
    project = user_copy.pop("project")
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project},
        json=user_copy,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST


def test_existing_user_change_ownership(client):
    """Change user role in project to project owner."""
    project = models.Project.query.filter_by(
        public_id=change_owner_existing_user["project"]
    ).one_or_none()
    user = models.Email.query.filter_by(email=change_owner_existing_user["email"]).one_or_none()
    project_user = models.ProjectUsers.query.filter(
        sqlalchemy.and_(
            models.ProjectUsers.user_id == user.user_id,
            models.ProjectUsers.project_id == project.id,
        )
    ).one_or_none()

    assert not project_user.owner

    user_new_owner_status = change_owner_existing_user.copy()
    project = user_new_owner_status.pop("project")
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project},
        json=user_new_owner_status,
    )

    assert response.status_code == http.HTTPStatus.OK

    db.session.refresh(project_user)

    assert project_user.owner


def test_existing_user_change_ownership_same_permissions(client):
    """Try to change role in project to same role."""
    user_same_ownership = submit_with_same_ownership.copy()
    project = user_same_ownership.pop("project")
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project},
        json=user_same_ownership,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_add_existing_user_with_unsuitable_role(client):
    """Cannot add unit admins to projects. They have access to all."""
    user_with_unsuitable_role = existing_research_user_to_existing_project.copy()
    user_with_unsuitable_role["role"] = "Unit Admin"
    project = user_with_unsuitable_role.pop("project")
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project},
        json=user_with_unsuitable_role,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN


# Invite to project ########################################################### Invite to project #


def test_invite_with_project_by_unituser(client):
    "Test that a new invite including a project can be created"
    project = existing_project
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project},
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user
    assert invited_user.email == first_new_user["email"]
    assert invited_user.role == first_new_user["role"]

    assert invited_user.nonce is not None
    assert invited_user.public_key is not None
    assert invited_user.private_key is not None

    project_invite_keys = invited_user.project_invite_keys
    assert len(project_invite_keys) == 1
    assert project_invite_keys[0].project.public_id == project
    assert not project_invite_keys[0].owner


def test_add_project_to_existing_invite_by_unituser(client):
    "Test that a project can be associated with an existing invite"

    # Create invite upfront

    project = existing_project
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()

    # Check that the invite has no projects yet

    assert invited_user
    assert len(invited_user.project_invite_keys) == 0

    # Add project to existing invite

    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project},
        json=first_new_user,
    )

    assert response.status_code == http.HTTPStatus.OK

    # Check that the invite has now a project association
    project_invite_keys = invited_user.project_invite_keys
    assert len(project_invite_keys) == 1
    assert project_invite_keys[0].project.public_id == project
    assert not project_invite_keys[0].owner


def test_update_project_to_existing_invite_by_unituser(client):
    "Test that project ownership can be updated for an existing invite"

    # Create Invite upfront

    project = existing_project
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project},
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_obj = models.Project.query.filter_by(public_id=existing_project).one_or_none()
    invite_obj = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()

    project_invite = models.ProjectInviteKeys.query.filter(
        sqlalchemy.and_(
            models.ProjectInviteKeys.invite_id == invite_obj.id,
            models.ProjectUserKeys.project_id == project_obj.id,
        )
    ).one_or_none()

    assert project_invite
    assert not project_invite.owner

    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project},
        json=first_new_owner,
    )

    assert response.status_code == http.HTTPStatus.OK

    db.session.refresh(project_invite)

    assert project_invite.owner


def test_invited_as_owner_and_researcher_to_different_project(client):
    "Test that an invite can be owner of one project and researcher of another"

    # Create Invite upfront as owner

    project = existing_project
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project},
        json=first_new_owner,
    )
    assert response.status_code == http.HTTPStatus.OK

    # Perform second invite as researcher
    project2 = existing_project_2
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project2},
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    project_obj_owner = models.Project.query.filter_by(public_id=existing_project).one_or_none()
    project_obj_not_owner = models.Project.query.filter_by(
        public_id=existing_project_2
    ).one_or_none()

    invite_obj = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()

    project_invite_owner = models.ProjectInviteKeys.query.filter(
        sqlalchemy.and_(
            models.ProjectInviteKeys.invite_id == invite_obj.id,
            models.ProjectInviteKeys.project_id == project_obj_owner.id,
        )
    ).one_or_none()

    assert project_invite_owner
    assert project_invite_owner.owner

    project_invite_not_owner = models.ProjectInviteKeys.query.filter(
        sqlalchemy.and_(
            models.ProjectInviteKeys.invite_id == invite_obj.id,
            models.ProjectInviteKeys.project_id == project_obj_not_owner.id,
        )
    ).one_or_none()

    assert project_invite_not_owner
    assert not project_invite_not_owner.owner

    # Owner or not should not be stored on the invite
    assert invite_obj.role == "Researcher"


def test_invite_to_project_by_project_owner(client):
    "Test that a project owner can invite to its project"

    project = existing_project
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client),
        query_string={"project": project},
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user
    assert invited_user.email == first_new_user["email"]
    assert invited_user.role == first_new_user["role"]

    assert invited_user.nonce is not None
    assert invited_user.public_key is not None
    assert invited_user.private_key is not None

    project_invite_keys = invited_user.project_invite_keys
    assert len(project_invite_keys) == 1
    assert project_invite_keys[0].project.public_id == project
    assert not project_invite_keys[0].owner


def test_add_anyuser_to_project_with_superadmin(client):
    """Super admins cannot invite to project."""
    project = existing_project
    for x in [first_new_user, first_new_owner, new_unit_user, new_unit_admin]:
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
            query_string={"project": project},
            json=x,
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST

        # An invite should not have been created
        invited_user = models.Invite.query.filter_by(email=x["email"]).one_or_none()
        assert not invited_user


def test_add_unituser_and_admin_no_unit_with_superadmin(client):
    """A super admin needs to specify a unit to be able to invite unit users."""
    project = existing_project
    for x in [new_unit_user, new_unit_admin]:
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
            json=x,
        )

        assert "You need to specify a unit" in response.json["message"]
        assert response.status_code == http.HTTPStatus.BAD_REQUEST

        invited_user = models.Invite.query.filter_by(email=x["email"]).one_or_none()
        assert not invited_user


def test_add_researchuser_project_no_access_unit_admin_and_personnel(client):
    """A unit admin and personnel should not be able to give access to a project
    which they themselves have lost access to."""
    # Make sure the project exists
    project = models.Project.query.filter_by(public_id=existing_project).one_or_none()
    assert project

    for inviter in ["unitadmin", "unituser", "projectowner"]:
        # Check that the unit admin has access to the project first
        project_user_key = models.ProjectUserKeys.query.filter_by(
            user_id=inviter, project_id=project.id
        ).one_or_none()
        assert project_user_key

        # Remove the project access (for test)
        db.session.delete(project_user_key)

        # Make sure the project access does not exist now
        project_user_key = models.ProjectUserKeys.query.filter_by(
            user_id=inviter, project_id=project.id
        ).one_or_none()
        assert not project_user_key

        for x in [first_new_user, first_new_owner]:
            # Make sure there is no ongoing invite
            invited_user_before = models.Invite.query.filter_by(email=x["email"]).one_or_none()
            if invited_user_before:
                db.session.delete(invited_user_before)
            invited_user_before = models.Invite.query.filter_by(email=x["email"]).one_or_none()
            assert not invited_user_before

            # Attempt invite
            response = client.post(
                tests.DDSEndpoint.USER_ADD,
                headers=tests.UserAuth(tests.USER_CREDENTIALS[inviter]).token(client),
                json=x,
                query_string={"project": project.public_id},
            )

            # The invite should still be done, but they can't invite to a project
            invited_user = models.Invite.query.filter_by(email=x["email"]).one_or_none()
            assert invited_user

            # Make sure there are no project v
            assert not invited_user.project_invite_keys

            # There should be an error message
            assert response.status_code == http.HTTPStatus.BAD_REQUEST
            assert "The user could not be added to the project(s)" in response.json["message"]

            # Verify ok error messages
            assert "errors" in response.json
            assert project.public_id in response.json["errors"]
            assert (
                "You do not have access to the specified project."
                in response.json["errors"][project.public_id]
            )


# Invite without email
def test_invite_without_email(client):
    """The email is required."""
    user_no_email = first_new_user.copy()
    user_no_email.pop("email")

    for inviter in ["superadmin", "unitadmin", "unituser"]:
        # Attempt invite
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS[inviter]).token(client),
            json=user_no_email,
            # query_string={"project": existing_project},
        )

        # There should be an error message
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Email address required to add or invite." in response.json["message"]


# Invite super admin with unit admin
def test_invite_superadmin_as_unitadmin(client):
    """A unit admin cannt invie a superadmin"""
    # Attempt invite
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=new_super_admin,
    )

    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "You do not have the necessary permissions." in response.json["message"]


# Invite super admin and unit admin with unit personnel
def test_invite_superadmin_and_unitadmin_as_unitpersonnel(client):
    """A unit personnel cannot invite a superadmin or unit admin"""
    for invitee in [new_super_admin, new_unit_admin]:
        # Attempt invite
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
            json=invitee,
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN
        assert "You do not have the necessary permissions." in response.json["message"]


# Invite super admin, unit admin or unit personnel
def test_invite_superadmin_and_unitadmin_and_unitpersonnel_as_projectowner(client):
    """A project owner cannot invite a superadmin or unit admin or unit personnel."""
    for invitee in [new_super_admin, new_unit_admin, new_unit_user]:
        # Attempt invite
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client),
            json=invitee,
            query_string={"project": existing_project},
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN
        assert "You do not have the necessary permissions." in response.json["message"]


def test_invite_unituser_as_superadmin_incorrect_unit(client):
    """A valid unit is required for super admins to invite unit users."""
    for invitee in [new_unit_admin, new_unit_user]:
        invite_with_invalid_unit = invitee.copy()
        invite_with_invalid_unit["unit"] = "invalidunit"

        # Attempt invite
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
            json=invite_with_invalid_unit,
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Invalid unit public id." in response.json["message"]


def test_invite_unituser_with_valid_unit_as_superadmin(client):
    """A unit user should be invited if the super admin provides a valid unit."""
    for invitee in [new_unit_admin, new_unit_user]:
        valid_unit = models.Unit.query.filter_by(name="Unit 1").one_or_none()
        assert valid_unit

        invite_with_valid_unit = invitee.copy()
        invite_with_valid_unit["unit"] = valid_unit.public_id

        # Attempt invite
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
            json=invite_with_valid_unit,
        )

        new_invite = models.Invite.query.filter_by(
            email=invite_with_valid_unit["email"]
        ).one_or_none()
        assert new_invite


# -- timestamp


def test_invite_users_should_have_different_timestamps(client):
    """Invites should not get the same timestamps in the database."""
    # Current time
    real_time = current_time()

    # Set initial time
    new_time_initial = datetime(year=2022, month=9, day=12, hour=15, minute=49, second=10)
    assert real_time != new_time_initial

    # Use freezegun
    import freezegun

    with freezegun.freeze_time(new_time_initial):
        start_time = current_time()
        assert start_time == new_time_initial

    # Invite researcher
    researcher_info = {"role": "Researcher", "email": "newresearcher@test.com"}
    new_time_1 = new_time_initial + timedelta(days=1)
    with freezegun.freeze_time(new_time_1):
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
            json=researcher_info,
        )
        assert response.status_code == http.HTTPStatus.OK

    # Check invite created time
    researcher_invite: models.Invite = models.Invite.query.filter_by(
        email=researcher_info["email"], role=researcher_info["role"]
    ).one_or_none()
    assert researcher_invite
    assert new_time_initial != researcher_invite.created_at == new_time_1

    # Invite Unit Personnel
    unit: models.Unit = models.Unit.query.first()
    assert unit

    unitpersonnel_info = {
        "role": "Unit Personnel",
        "email": "newunitpersonnel@test.com",
        "unit": unit.public_id,
    }
    new_time_2 = new_time_1 + timedelta(days=1)
    with freezegun.freeze_time(new_time_2):
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
            json=unitpersonnel_info,
        )
        assert response.status_code == http.HTTPStatus.OK

    # Check invite created time
    unitpersonnel_invite: models.Invite = models.Invite.query.filter_by(
        email=unitpersonnel_info["email"], role=unitpersonnel_info["role"]
    ).one_or_none()
    assert unitpersonnel_invite
    assert (
        unitpersonnel_invite.created_at == new_time_2
        and unitpersonnel_invite.created_at not in [new_time_initial, new_time_1]
    )

    # Invite Unit Admin
    unit: models.Unit = models.Unit.query.first()
    assert unit

    unitadmin_info = {
        "role": "Unit Admin",
        "email": "newunitadmin@test.com",
        "unit": unit.public_id,
    }
    new_time_3 = new_time_2 + timedelta(days=1, hours=3)
    with freezegun.freeze_time(new_time_3):
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
            json=unitadmin_info,
        )
        assert response.status_code == http.HTTPStatus.OK

    # Check invite created time
    unitadmin_invite: models.Invite = models.Invite.query.filter_by(
        email=unitadmin_info["email"], role=unitadmin_info["role"]
    ).one_or_none()
    assert unitadmin_invite
    assert unitadmin_invite.created_at == new_time_3 and unitadmin_invite.created_at not in [
        new_time_initial,
        new_time_1,
        new_time_2,
    ]

    # Invite Super Admin
    superadmin_info = {"role": "Super Admin", "email": "newsuperadmin@test.com"}
    new_time_4 = new_time_3 + timedelta(days=1, hours=6)
    with freezegun.freeze_time(new_time_4):
        response: werkzeug.test.WrapperTestResponse = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
            json=superadmin_info,
        )
        assert response.status_code == http.HTTPStatus.OK

    # Check invite created time
    superadmin_invite: models.Invite = models.Invite.query.filter_by(
        email=superadmin_info["email"], role=superadmin_info["role"]
    ).one_or_none()
    assert superadmin_invite
    assert superadmin_invite.created_at == new_time_4 and superadmin_invite.created_at not in [
        new_time_initial,
        new_time_1,
        new_time_2,
        new_time_3,
    ]


def test_list_invites(client):
    """
    Confirm that users can list relevant invites

    * Researcher who do not own any projects cannot see invites
    * Researcher who own a project can see invites for that project
    * Unit admin|personnel can see invites to any projects owned by the unit, and invites to the unit
    * Superadmin can see any invites
    * All invites contain columns for email, role, created_at, public_id
    * Invites for unit admin|personnel also includes unit column for superadmin
    """

    def invite_user(user_data: str, as_user: str) -> dict:
        params = "?"
        if "project" in user_data:
            params += f"project={user_data['project']}&"
        return client.post(
            tests.DDSEndpoint.USER_ADD + params,
            headers=tests.UserAuth(tests.USER_CREDENTIALS[as_user]).token(client),
            json=user_data,
        )

    def get_list(as_user) -> dict:
        return client.get(
            tests.DDSEndpoint.LIST_INVITES,
            headers=tests.UserAuth(tests.USER_CREDENTIALS[as_user]).token(client),
        )

    unit_invite = dict(new_unit_user)
    unit_invite["unit"] = "Unit 1"
    invite_user(unit_invite, "unitadmin")
    unit_invite["unit"] = "The league of the extinct gentlemen"
    invite_user(unit_invite, "superadmin")
    invite_user(new_super_admin, "superadmin")

    researcher_to_project = dict(first_new_user_existing_project)
    invite_user(researcher_to_project, "unitadmin")
    researcher_to_project["project"] = "second_public_project_id"
    invite_user(researcher_to_project, "unitadmin")
    researcher_to_project["project"] = "unit2testing"
    invite_user(researcher_to_project, "unitadmin")

    researcher_to_project = dict(new_owner_existing_project)
    invite_user(researcher_to_project, "unitadmin")
    researcher_to_project["project"] = "second_public_project_id"
    invite_user(researcher_to_project, "unitadmin")
    researcher_to_project["project"] = "unit2testing"
    invite_user(researcher_to_project, "unitadmin")

    response = get_list("superadmin")
    assert "invites" in response.json
    assert len(response.json["invites"]) == 6
    for entry in response.json["invites"]:
        for key in ["Email", "Role", "Projects", "Created", "Unit"]:
            assert key in entry
        if entry["Role"] in ("Unit Admin", "Unit Personnel"):
            assert entry["Unit"] == "Unit 1"
            assert isinstance(entry["Projects"], list)
        elif entry["Role"] in ("Unit Admin", "Unit Personnel"):
            assert entry["Projects"] == "----"
    assert response.json.get("keys", []) == ["Email", "Unit", "Role", "Projects", "Created"]

    response = get_list("unitadmin")
    assert "invites" in response.json
    assert len(response.json["invites"]) == 3
    for entry in response.json["invites"]:
        for key in ["Email", "Role", "Projects", "Created"]:
            assert key in entry
        if entry["Role"] in ("Unit Admin", "Unit Personnel"):
            assert len(entry["Projects"]) == 5
            assert isinstance(entry["Projects"], list)
        elif entry["Role"] == "Researcher":
            assert len(entry["Projects"]) == 2
            assert isinstance(entry["Projects"], list)
        elif entry["Role"] == "Superadmin":  # Should never happen
            assert False
        assert "Unit" not in entry
    assert response.json.get("keys", []) == ["Email", "Role", "Projects", "Created"]

    response = get_list("projectowner")
    assert "invites" in response.json
    assert len(response.json["invites"]) == 2
    for entry in response.json["invites"]:
        for key in ["Email", "Role", "Projects", "Created"]:
            assert key in entry
        assert "Unit" not in entry
        assert len(entry["Projects"]) == 1
        assert isinstance(entry["Projects"], list)
    assert response.json.get("keys", []) == ["Email", "Role", "Projects", "Created"]

    response = get_list("researchuser")
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert not response.json.get("invites")
    assert not response.json.get("keys")


##### Test for RemoveUserAssociation


def test_remove_access_invite_associated_several_projects(client):
    """If an invite is associated with several projects then a single revoke access should not delete the invite"""

    project_1, project_2 = get_existing_projects()

    # invite a new user to both projects
    invited_user = invite_to_project(project=project_1, client=client, json_query=first_new_user)
    _ = invite_to_project(project=project_2, client=client, json_query=first_new_user)

    # Now revoke access for the first project
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project_1.public_id},
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    assert (
        f"Invited user is no longer associated with the project '{project_1.public_id}'."
        in response.json["message"]
    )

    # The project invite row should only be deleted for project 1 and the invite should still exist
    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user

    project_invite_keys = models.ProjectInviteKeys.query.filter_by(
        invite_id=invited_user.id, project_id=project_2.id
    ).one_or_none()
    assert project_invite_keys

    project_invite_keys = models.ProjectInviteKeys.query.filter_by(
        invite_id=invited_user.id, project_id=project_1.id
    ).one_or_none()
    assert not project_invite_keys


def test_revoking_access_to_unacepted_invite(client):
    """Revoking access to an unacepted invite for an existing project should delete the invite from the db"""

    project, _ = get_existing_projects()

    # Invite a new user to the project
    invited_user = invite_to_project(project=project, client=client, json_query=first_new_user)
    invited_user_id = invited_user.id

    # Now, revoke access to said user. The invite should be deleted
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project.public_id},
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.OK

    assert (
        f"Invited user is no longer associated with the project '{project.public_id}'."
        in response.json["message"]
    )

    # Check that the invite is deleted
    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert not invited_user

    project_invite_keys = models.ProjectInviteKeys.query.filter_by(
        invite_id=invited_user_id, project_id=project.id
    ).one_or_none()
    assert not project_invite_keys


def test_remove_nonacepted_user_from_other_project(client, boto3_session):
    """Try to remove an User with an unacepted invite from another project should result in an error"""

    project_1, project_2 = get_existing_projects()

    # invite a new user to a project
    invite_to_project(project=project_1, client=client, json_query=first_new_user)

    # try to remove the same user from a different one
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project_2.public_id},
        json=first_new_user,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Cannot remove non-existent project access" in response.json["message"]


def test_researcher_removes_project_owner(client):
    """
    A Researcher who is not a PO should not be able to delete a PO
    """

    project, _ = get_existing_projects()

    # Research user trying to delete PO
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        query_string={"project": project.public_id},
        json=remove_user_project_owner,
    )

    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "Insufficient credentials" in response.json["message"]


def test_unit_personnel_removed(client):
    """
    Unit Personnel cannot be deleted from individual projects (they should be removed from the unit instead)
    """
    project, _ = get_existing_projects()

    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project.public_id},
        json=remove_user_unit_user,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    # Should give error because a unit personal cannot be granted access to individual projects
    assert "Cannot remove non-existent project access." in response.json["message"]


def test_removed_myself(client):
    """
    An User cannot remove themselves from a project
    """
    project, _ = get_existing_projects()

    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client),
        query_string={"project": project.public_id},
        json=remove_user_project_owner,
    )

    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "You cannot revoke your own access" in response.json["message"]


def test_remove_invite_unit_admin(client):
    """
    A project removal request for an unanswered invite of unit admin should not work
    """
    project, _ = get_existing_projects()

    # invite a new unit admin to the system
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=first_new_user_unit_admin,
    )
    assert response.status_code == http.HTTPStatus.OK

    # try to remove the unitadmin for a specific project within their unit -> should not work
    email = first_new_user_unit_admin["email"]
    rem_user = {"email": email}
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project.public_id},
        json=rem_user,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    # Should give error because a unit personal cannot be granted access to individual projects
    assert (
        "Cannot remove a Unit Admin / Unit Personnel from individual projects"
        in response.json["message"]
    )


def test_invite_unit_user(client):
    """
    A project removal request for an unanswered invite of unit personel should not work
    """
    project, _ = get_existing_projects()

    # invite a new unit user to the system
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=first_new_user_unit_personel,
    )
    assert response.status_code == http.HTTPStatus.OK

    # try to remove the Unit Personnel for a specific project within their unit -> should not work
    email = first_new_user_unit_personel["email"]
    rem_user = {"email": email}
    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        query_string={"project": project.public_id},
        json=rem_user,
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    # Should give error because a Unit Personnel cannot be granted access to individual projects
    assert (
        "Cannot remove a Unit Admin / Unit Personnel from individual projects"
        in response.json["message"]
    )
