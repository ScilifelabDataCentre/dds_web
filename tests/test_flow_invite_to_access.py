import unittest

import flask

import tests
from dds_web.database import models
import dds_web.api.user
from dds_web.security.tokens import encrypted_jwt_token

# Invitation to Registration ######################################### Invitation to Registration #

# I have a feeling these tests will be extra hard to figure out why they fail so:
DEBUG = False


REGISTRATION_DATA = {
    "name": "Test User",
    "username": "user_not_existing",
    "password": "Password123",
    "confirm": "Password123",
    "submit": "submit",
}


def perform_invite(client, inviting_user, email, role=None, project=None):
    json_data = {"email": email, "role": role}
    query_string = {}
    if project:
        if not role:
            raise ValueError("Role must be specified when inviting to a project")
        query_string = {"project": project.public_id}

    # get the auth token here to avoid interfering with the invite token fetching
    auth_token = tests.UserAuth(tests.USER_CREDENTIALS[inviting_user.username]).token(client)

    # Need to get hold of the actual invite token
    invite_token = None
    with unittest.mock.patch.object(
        dds_web.api.user, "encrypted_jwt_token", return_value="token"
    ) as mock_token_method:
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=auth_token,
            query_string=query_string,
            json=json_data,
            content_type="application/json",
        )
        if DEBUG:
            print(response.data)
        # New invite token is not generated if invite is already sent
        assert mock_token_method.call_count <= 1
        if mock_token_method.call_args is not None:
            call_args = mock_token_method.call_args
            invite_token = encrypted_jwt_token(*call_args.args, **call_args.kwargs)

    if response.status != "200 OK":
        if DEBUG:
            print(response.status_code)
        raise ValueError(f"Invitation failed: {response.data}")

    return invite_token


def get_private(client, project, auth_token):
    """Request decrypted project private key for user just created
    to somewhat test that the decryption works"""
    response = client.get(
        tests.DDSEndpoint.PROJ_PRIVATE,
        query_string={"project": project.public_id},
        headers=auth_token,
    )
    assert (
        response.status == "200 OK"
    ), f"Unable to fetch project private key for project: {project}, response: {response.data}"


def invite_confirm_register_and_get_private(
    client, inviting_user, email, projects, role_per_project=None
):
    # Invite
    if projects is None or projects == []:
        assert len(role_per_project) == 1
        invite_token = perform_invite(client, inviting_user, email, role=role_per_project[0])
    else:
        for project, role in zip(projects, role_per_project):
            most_recent_invite_token = perform_invite(
                client, inviting_user, email, role=role, project=project
            )
            # only the first invite returns a token
            if most_recent_invite_token is not None:
                invite_token = most_recent_invite_token

    if DEBUG:
        print([(invite.email, invite.role) for invite in models.Invite.query.all()])
        print(
            [
                (pik.project.public_id, pik.invite.email, pik.owner)
                for pik in models.ProjectInviteKeys.query.all()
            ]
        )

    # Confirm invite
    response = client.get(
        tests.DDSEndpoint.USER_CONFIRM + invite_token, content_type="application/json"
    )
    assert response.status == "200 OK"

    # Complete registration
    form_token = flask.g.csrf_token

    form_data = {**REGISTRATION_DATA, "csrf_token": form_token, "email": email}

    response = client.post(
        tests.DDSEndpoint.USER_NEW,
        json=form_data,
        follow_redirects=True,
    )
    assert response.status == "200 OK"

    user = models.User.query.filter_by(username=form_data["username"]).one_or_none()

    auth_token = tests.UserAuth(f"{form_data['username']}:{form_data['password']}").token(client)

    if projects is not None:
        for project in projects:
            # Request decrypted project private key for user just created
            # to somewhat test that the decryption works
            get_private(client, project, auth_token)

    return user


# Researcher invited by Unit Admin ############################# Researcher invited by Unit Admin #


def test_invite_to_register_researcher_without_project_by_unitadmin(client):
    "Test that a user without a project can be created by unitadmin"
    unitadmin = models.User.query.filter_by(username="unitadmin").one_or_none()
    researcher_to_be = "researcher_to_be@example.org"

    user = invite_confirm_register_and_get_private(
        client,
        inviting_user=unitadmin,
        email=researcher_to_be,
        projects=None,
        role_per_project=["Researcher"],
    )
    assert user.role == "Researcher"
    assert user.is_active
    assert user.projects == []
    assert user.project_user_keys == []


def test_invite_to_register_researcher_with_project_by_unitadmin(client):
    "Test that a researchuser with project access can be created by unitadmin"
    unitadmin = models.User.query.filter_by(username="unitadmin").one_or_none()
    researcher_to_be = "researcher_to_be@example.org"
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()

    user = invite_confirm_register_and_get_private(
        client,
        inviting_user=unitadmin,
        email=researcher_to_be,
        projects=[project],
        role_per_project=["Researcher"],
    )
    assert user.role == "Researcher"
    assert user.is_active

    assert len(user.projects) == 1
    assert user.projects[0].public_id == project.public_id
    assert len(user.project_associations) == 1
    for project_user in user.project_associations:
        assert not project_user.owner

    assert len(user.project_user_keys) == 1
    assert user.project_user_keys[0].project_id == project.id


def test_invite_to_register_researcher_with_multiple_projects_by_unitadmin(client):
    "Test that a researchuser with project access including project ownership can be created by unitadmin"
    unitadmin = models.User.query.filter_by(username="unitadmin").one_or_none()
    researcher_to_be = "researcher_to_be@example.org"
    project1 = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    project2 = models.Project.query.filter_by(public_id="second_public_project_id").one_or_none()

    user = invite_confirm_register_and_get_private(
        client,
        inviting_user=unitadmin,
        email=researcher_to_be,
        projects=[project1, project2],
        role_per_project=["Researcher", "Project Owner"],
    )
    assert user.role == "Researcher"
    assert user.is_active

    assert len(user.projects) == 2
    assert len(user.project_associations) == 2
    for project_user in user.project_associations:
        if project_user.project.public_id == project1.public_id:
            assert not project_user.owner
        else:
            assert project_user.owner

    assert len(user.project_user_keys) == 2


# Researcher invited by Unit User ############################# Researcher invited by Unit User #


def test_invite_to_register_researcher_without_project_by_unituser(client):
    "Test that a user without a project can be created"
    unituser = models.User.query.filter_by(username="unituser").one_or_none()
    researcher_to_be = "researcher_to_be@example.org"

    user = invite_confirm_register_and_get_private(
        client,
        inviting_user=unituser,
        email=researcher_to_be,
        projects=None,
        role_per_project=["Researcher"],
    )
    assert user.role == "Researcher"
    assert user.is_active
    assert user.projects == []
    assert user.project_user_keys == []


def test_invite_to_register_researcher_with_project_by_unituser(client):
    "Test that a researchuser with project access can be created by unituser"
    unituser = models.User.query.filter_by(username="unituser").one_or_none()
    researcher_to_be = "researcher_to_be@example.org"
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()

    user = invite_confirm_register_and_get_private(
        client,
        inviting_user=unituser,
        email=researcher_to_be,
        projects=[project],
        role_per_project=["Researcher"],
    )
    assert user.role == "Researcher"
    assert user.is_active

    assert len(user.projects) == 1
    assert user.projects[0].public_id == project.public_id
    assert len(user.project_associations) == 1
    for project_user in user.project_associations:
        assert not project_user.owner

    assert len(user.project_user_keys) == 1
    assert user.project_user_keys[0].project_id == project.id


def test_invite_to_register_researcher_with_multiple_projects_by_unituser(client):
    "Test that a researchuser with project access including project ownership can be created by unituser"
    unituser = models.User.query.filter_by(username="unituser").one_or_none()
    researcher_to_be = "researcher_to_be@example.org"
    project1 = models.Project.query.filter_by(public_id="public_project_id").one_or_none()
    project2 = models.Project.query.filter_by(public_id="second_public_project_id").one_or_none()

    user = invite_confirm_register_and_get_private(
        client,
        inviting_user=unituser,
        email=researcher_to_be,
        projects=[project1, project2],
        role_per_project=["Researcher", "Project Owner"],
    )
    assert user.role == "Researcher"
    assert user.is_active

    assert len(user.projects) == 2
    assert len(user.project_associations) == 2
    for project_user in user.project_associations:
        if project_user.project.public_id == project1.public_id:
            assert not project_user.owner
        else:
            assert project_user.owner

    assert len(user.project_user_keys) == 2


# Researcher invited by Project Owner ############################# Researcher invited by Project Owner #


def test_invite_to_register_researcher_with_project_by_project_owner(client):
    "Test that a researchuser with project access can be created by project owner"
    project_owner = models.User.query.filter_by(username="projectowner").one_or_none()
    researcher_to_be = "researcher_to_be@example.org"
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()

    user = invite_confirm_register_and_get_private(
        client,
        inviting_user=project_owner,
        email=researcher_to_be,
        projects=[project],
        role_per_project=["Researcher"],
    )
    assert user.role == "Researcher"
    assert user.is_active

    assert len(user.projects) == 1
    assert user.projects[0].public_id == project.public_id
    assert len(user.project_associations) == 1
    for project_user in user.project_associations:
        assert not project_user.owner

    assert len(user.project_user_keys) == 1
    assert user.project_user_keys[0].project_id == project.id


def test_invite_to_register_researcher_with_project_as_owner_by_project_owner(client):
    "Test that a researchuser with project access can be created as project owner by project owner"
    project_owner = models.User.query.filter_by(username="projectowner").one_or_none()
    researcher_to_be = "researcher_to_be@example.org"
    project = models.Project.query.filter_by(public_id="public_project_id").one_or_none()

    user = invite_confirm_register_and_get_private(
        client,
        inviting_user=project_owner,
        email=researcher_to_be,
        projects=[project],
        role_per_project=["Project Owner"],
    )
    assert user.role == "Researcher"
    assert user.is_active

    assert len(user.projects) == 1
    assert user.projects[0].public_id == project.public_id
    assert len(user.project_associations) == 1
    for project_user in user.project_associations:
        assert project_user.owner

    assert len(user.project_user_keys) == 1
    assert user.project_user_keys[0].project_id == project.id


# Unituser invited by Unit Admin ################################# Unituser invited by Unit Admin #


def test_invite_to_register_unituser_by_unitadmin(client):
    "Test that a unit user can be created with project access"
    unitadmin = models.User.query.filter_by(username="unitadmin").one_or_none()
    unituser_to_be = "unituser_to_be@example.org"

    projects = set(unitadmin.projects)
    assert len(projects) > 1

    user = invite_confirm_register_and_get_private(
        client,
        inviting_user=unitadmin,
        email=unituser_to_be,
        projects=None,
        role_per_project=["Unit Personnel"],
    )
    assert user.role == "Unit Personnel"
    assert user.is_active
    assert set(user.projects) == projects
    assert len(user.project_user_keys) == len(projects)

    auth_token = tests.UserAuth(f"{user.username}:{REGISTRATION_DATA['password']}").token(client)

    for project in projects:
        get_private(client, project, auth_token)
