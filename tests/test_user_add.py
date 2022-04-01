from urllib import response
import dds_web
import flask_mail
import http
import json
import sqlalchemy
from dds_web import db
from dds_web.database import models
import tests
import pytest
import unittest
import marshmallow

existing_project = "public_project_id"
existing_project_2 = "second_public_project_id"
first_new_email = {"email": "first_test_email@mailtrap.io"}
first_new_user = {**first_new_email, "role": "Researcher"}
first_new_owner = {**first_new_email, "role": "Project Owner"}
first_new_user_existing_project = {**first_new_user, "project": "public_project_id"}
first_new_user_extra_args = {**first_new_user, "extra": "test"}
first_new_user_invalid_role = {**first_new_email, "role": "Invalid Role"}
first_new_user_invalid_email = {"email": "first_invalid_email", "role": first_new_user["role"]}
existing_invite = {"email": "existing_invite_email@mailtrap.io", "role": "Researcher"}
new_unit_admin = {"email": "new_unit_admin@mailtrap.io", "role": "Unit Admin"}
new_super_admin = {"email": "new_super_admin@mailtrap.io", "role": "Super Admin"}
new_unit_user = {"email": "new_unit_user@mailtrap.io", "role": "Unit Personnel"}
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

# Inviting Users ################################################################# Inviting Users #
def test_add_user_with_researcher(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        json=first_new_user,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user is None


def test_add_user_with_unituser_no_role(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json=first_new_email,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    invited_user = models.Invite.query.filter_by(email=first_new_email["email"]).one_or_none()
    assert invited_user is None


def test_add_user_with_unitadmin_with_extraargs(client):
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
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=new_unit_admin,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    invited_user = models.Invite.query.filter_by(email=new_unit_admin["email"]).one_or_none()
    assert invited_user is None


# Add existing users to projects ################################# Add existing users to projects #
def test_add_existing_user_without_project(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        json=existing_research_user,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST


def test_research_user_cannot_add_existing_user_to_existing_project(client):
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
        assert "Invalid unit publid id." in response.json["message"]


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
