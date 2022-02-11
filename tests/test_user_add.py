import http
import json
import sqlalchemy
from dds_web import db
from dds_web.database import models
import tests
import pytest
import marshmallow

first_new_email = {"email": "first_test_email@mailtrap.io"}
first_new_user = {**first_new_email, "role": "Researcher"}
first_new_user_extra_args = {**first_new_user, "extra": "test"}
first_new_user_invalid_role = {**first_new_email, "role": "Invalid Role"}
first_new_user_invalid_email = {"email": "first_invalid_email", "role": first_new_user["role"]}
existing_invite = {"email": "existing_invite_email@mailtrap.io", "role": "Researcher"}
new_unit_admin = {"email": "new_unit_admin@mailtrap.io", "role": "Super Admin"}
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


def test_add_user_with_researcher(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).token(client),
        data=json.dumps(first_new_user),
        content_type="application/json",
    )
    response.status_code == http.HTTPStatus.FORBIDDEN
    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user is None


def test_add_user_with_unituser_no_role(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps(first_new_email),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    invited_user = models.Invite.query.filter_by(email=first_new_email["email"]).one_or_none()
    assert invited_user is None


def test_add_user_with_unitadmin_with_extraargs(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps(first_new_user_extra_args),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    invited_user = models.Invite.query.filter_by(
        email=first_new_user_extra_args["email"]
    ).one_or_none()
    assert invited_user is None


def test_add_user_with_unitadmin_and_invalid_role(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps(first_new_user_invalid_role),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    invited_user = models.Invite.query.filter_by(
        email=first_new_user_invalid_role["email"]
    ).one_or_none()
    assert invited_user is None


def test_add_user_with_unitadmin_and_invalid_email(client):
    with pytest.raises(marshmallow.ValidationError):
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
            data=json.dumps(first_new_user_invalid_email),
            content_type="application/json",
        )

    invited_user = models.Invite.query.filter_by(
        email=first_new_user_invalid_email["email"]
    ).one_or_none()
    assert invited_user is None


def test_add_user_with_unitadmin(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps(first_new_user),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user
    assert invited_user.email == first_new_user["email"]
    assert invited_user.role == first_new_user["role"]


def test_add_user_with_superadmin(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
        data=json.dumps(first_new_user),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    invited_user = models.Invite.query.filter_by(email=first_new_user["email"]).one_or_none()
    assert invited_user
    assert invited_user.email == first_new_user["email"]
    assert invited_user.role == first_new_user["role"]


def test_add_user_existing_email(client):
    invited_user = models.Invite.query.filter_by(
        email=existing_invite["email"], role=existing_invite["role"]
    ).one_or_none()
    assert invited_user
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps(existing_invite),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST


def test_add_user_with_unitpersonnel_permission_denied(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        data=json.dumps(new_unit_admin),
        content_type="application/json",
    )
    response.status_code == http.HTTPStatus.FORBIDDEN

    invited_user = models.Invite.query.filter_by(email=new_unit_admin["email"]).one_or_none()
    assert invited_user is None


def test_add_existing_user_without_project(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        data=json.dumps(existing_research_user),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST


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
        data=json.dumps(user_copy),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    project_user_after_addition = models.ProjectUsers.query.filter(
        sqlalchemy.and_(
            models.ProjectUsers.user_id == user.user_id,
            models.ProjectUsers.project_id == project.id,
        )
    ).one_or_none()
    assert project_user_after_addition


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
        data=json.dumps({"new_status": "Available"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert project.current_status == "Available"

    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project_id},
        data=json.dumps(user_copy),
        content_type="application/json",
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
        data=json.dumps(user_copy),
        content_type="application/json",
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
        data=json.dumps(user_new_owner_status),
        content_type="application/json",
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
        data=json.dumps(user_same_ownership),
        content_type="application/json",
    )
    response.status_code == http.HTTPStatus.FORBIDDEN


def test_add_existing_user_with_unsuitable_role(client):
    user_with_unsuitable_role = existing_research_user_to_existing_project.copy()
    user_with_unsuitable_role["role"] = "Unit Admin"
    project = user_with_unsuitable_role.pop("project")
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project},
        data=json.dumps(user_with_unsuitable_role),
        content_type="application/json",
    )
    response.status_code == http.HTTPStatus.FORBIDDEN
