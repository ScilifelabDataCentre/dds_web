# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http

# Own
from dds_web import db
from dds_web.database import models
import tests


# CONFIG ################################################################################## CONFIG #

# proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}
proj_query = {"project": "public_project_id"}
# proj_query_restricted = {"project": "restricted_project_id"}
first_new_email = {"email": "first_test_email@mailtrap.io"}
first_new_user = {**first_new_email, "role": "Researcher"}

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


def delete_project_user(project_id, user_id, table_to_use):
    """Delete row in either ProjectUsers or ProjectUserKeys."""
    # Get project from database
    project = models.Project.query.filter_by(public_id=project_id).one_or_none()
    assert project

    # Delete projectuserkey and verify that it's deleted for user
    user_project_row = table_to_use.query.filter_by(project_id=project.id, user_id=user_id).first()
    if user_project_row:
        db.session.delete(user_project_row)
        db.session.commit()
    user_project_row = table_to_use.query.filter_by(project_id=project.id, user_id=user_id).first()
    assert not user_project_row

    return project


# TESTS #################################################################################### TESTS #


def test_fix_access_no_token(client):
    """Token required to fix project access."""
    response = client.post(tests.DDSEndpoint.PROJECT_ACCESS, headers=tests.DEFAULT_HEADER)
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    assert response.json.get("message")
    assert "No token" in response.json.get("message")


def test_fix_access_researcher_not_allowed(client):
    """Researcher cannot give access."""
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN


def test_fix_access_no_args(client):
    """User required to update access."""
    # Project Owner requires project info
    token = tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # Unit Personnel
    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing" in response.json.get("message")

    # Unit Personnel
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert "Required data missing" in response.json.get("message")


def test_fix_access_no_email(client):
    """Email required."""
    # No user
    token = tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"something": "notanemail"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert response.json.get("message") == "User email missing."


def test_fix_access_projectowner_with_invalid_email(client):
    """Project owner giving access to invalid email."""
    # No user
    token = tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "notanemail@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert response.json.get("message") == "User not found."


def test_fix_access_projectowner_valid_email_invalid_otheruser(client):
    """Project owner giving access to another user - no permissions."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "unituser1@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "You do not have the necessary permissions" in response.json.get("message")

    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "unitadmin@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "You do not have the necessary permissions" in response.json.get("message")


def test_fix_access_unituser_valid_email_invalid_otheruser(client):
    """Unit user giving access to Unit Admin - no permissions."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "unitadmin@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert "You do not have the necessary permissions" in response.json.get("message")


def test_fix_access_user_trying_themselves(client):
    """Unit user giving access to Unit Admin - no permissions."""
    token = tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "projectowner@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert response.json.get("message") == "You cannot renew your own access."

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "unituser1@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert response.json.get("message") == "You cannot renew your own access."

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "unitadmin@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    assert response.json.get("message") == "You cannot renew your own access."


def test_fix_access_projectowner_valid_email(client):
    """Project Owner giving access to users - ok."""
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    assert project

    user_project_row = models.ProjectUsers.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    assert user_project_row

    po_project_row = models.ProjectUsers.query.filter_by(
        project_id=project.id, user_id="projectowner"
    ).first()
    assert po_project_row and po_project_row.owner

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    if user_project_key_row:
        db.session.delete(user_project_key_row)
        db.session.commit()
    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    assert not user_project_key_row

    token = tests.UserAuth(tests.USER_CREDENTIALS["projectowner"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "researchuser@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.OK

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    assert user_project_key_row


def test_fix_access_unitpersonnel_valid_email_researcher(client):
    """Unit Personnel giving access to researcher - ok."""
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    assert project

    user_project_row = models.ProjectUsers.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    assert user_project_row

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    if user_project_key_row:
        db.session.delete(user_project_key_row)
        db.session.commit()
    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    assert not user_project_key_row

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "researchuser@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.OK

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    assert user_project_key_row


def test_fix_access_unitpersonnel_valid_email_projectowner(client):
    """Unit Personnel giving access to project owner - ok."""
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    assert project

    user_project_row = models.ProjectUsers.query.filter_by(
        project_id=project.id, user_id="projectowner"
    ).first()
    assert user_project_row

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="projectowner"
    ).first()
    if user_project_key_row:
        db.session.delete(user_project_key_row)
        db.session.commit()
    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="projectowner"
    ).first()
    assert not user_project_key_row

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "projectowner@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.OK

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="projectowner"
    ).first()
    assert user_project_key_row


def test_fix_access_unitpersonnel_valid_email_unitpersonnel(client):
    """Unit Personnel giving access to unit personnel - ok."""
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    assert project

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="unituser2"
    ).first()
    if user_project_key_row:
        db.session.delete(user_project_key_row)
        db.session.commit()
    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="unituser2"
    ).first()
    assert not user_project_key_row

    token = tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "unituser2@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.OK

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="unituser2"
    ).first()
    assert user_project_key_row


def test_fix_access_unitadmin_valid_email_researcher(client):
    """Unit Admin giving access to researcher - ok."""
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    assert project

    user_project_row = models.ProjectUsers.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    assert user_project_row

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    if user_project_key_row:
        db.session.delete(user_project_key_row)
        db.session.commit()
    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    assert not user_project_key_row

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "researchuser@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.OK

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    assert user_project_key_row


def test_fix_access_unitadmin_valid_email_projectowner(client):
    """Unit Admin giving access to project owner - ok."""
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    assert project

    user_project_row = models.ProjectUsers.query.filter_by(
        project_id=project.id, user_id="projectowner"
    ).first()
    assert user_project_row

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="projectowner"
    ).first()
    if user_project_key_row:
        db.session.delete(user_project_key_row)
        db.session.commit()
    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="projectowner"
    ).first()
    assert not user_project_key_row

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "projectowner@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.OK

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="projectowner"
    ).first()
    assert user_project_key_row


def test_fix_access_unitadmin_valid_email_unituser(client):
    """Unit Admin giving access to unituser - ok."""
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    assert project

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="unituser"
    ).first()
    if user_project_key_row:
        db.session.delete(user_project_key_row)
        db.session.commit()
    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="unituser"
    ).first()
    assert not user_project_key_row

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string=proj_query,
        json={"email": "unituser1@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.OK

    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="unituser"
    ).first()
    assert user_project_key_row


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
        f"Invited user is no longer associated with the project {project_1.public_id}."
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
        f"Invited user is no longer associated with the project {project.public_id}."
        in response.json["message"]
    )

    # Check that the invite is deleted
    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert not invited_user

    project_invite_keys = models.ProjectInviteKeys.query.filter_by(
        invite_id=invited_user_id, project_id=project.id
    ).one_or_none()
    assert not project_invite_keys


def test_fix_access_unitadmin_valid_email_unituser_no_project(client):
    """Unit Admin giving access to unituser - ok. No project."""
    # Remove ProjectUserKeys row for specific project and user
    project: models.Project = delete_project_user(
        project_id="public_project_id", user_id="unituser", table_to_use=models.ProjectUserKeys
    )

    # Fix access for user with no project specified
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        json={"email": "unituser1@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.OK

    # Verify that the projectuserkey row is fixed
    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="unituser"
    ).first()
    assert user_project_key_row


def test_fix_access_unitadmin_valid_email_researcher_no_projectuser_row(client):
    """Unit Admin giving access to researcher where there is no row in ProjectUsers table."""
    # Remove ProjectUserKeys row for specific project and user
    project: models.Project = delete_project_user(
        project_id="public_project_id", user_id="researchuser", table_to_use=models.ProjectUserKeys
    )

    # Delete projectuser row and verify that it's deleted for user
    _ = delete_project_user(
        project_id="public_project_id", user_id="researcher", table_to_use=models.ProjectUsers
    )

    # Fix access for user, project specified
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.post(
        tests.DDSEndpoint.PROJECT_ACCESS,
        headers=token,
        query_string={"project": project.public_id},
        json={"email": "researchuser@mailtrap.io"},
    )
    assert response.status_code == http.HTTPStatus.OK

    # Verify that the projectuserkey row is fixed
    user_project_key_row = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id="researchuser"
    ).first()
    assert user_project_key_row
