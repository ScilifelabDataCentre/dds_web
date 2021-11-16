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
    assert response.status == "403 FORBIDDEN"
    invited_user = (
        db.session.query(models.Invite).filter_by(email=first_new_user["email"]).one_or_none()
    )
    assert invited_user is None


def test_add_user_with_unituser_no_role(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps(first_new_email),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"
    invited_user = (
        db.session.query(models.Invite).filter_by(email=first_new_email["email"]).one_or_none()
    )
    assert invited_user is None


def test_add_user_with_unitadmin_with_extraargs(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps(first_new_user_extra_args),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"
    invited_user = (
        db.session.query(models.Invite)
        .filter_by(email=first_new_user_extra_args["email"])
        .one_or_none()
    )
    assert invited_user is None


def test_add_user_with_unitadmin_and_invalid_role(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps(first_new_user_invalid_role),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"
    invited_user = (
        db.session.query(models.Invite)
        .filter_by(email=first_new_user_invalid_role["email"])
        .one_or_none()
    )
    assert invited_user is None


def test_add_user_with_unitadmin_and_invalid_email(client):
    with pytest.raises(marshmallow.ValidationError):
        response = client.post(
            tests.DDSEndpoint.USER_ADD,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
            data=json.dumps(first_new_user_invalid_email),
            content_type="application/json",
        )

    invited_user = (
        db.session.query(models.Invite)
        .filter_by(email=first_new_user_invalid_email["email"])
        .one_or_none()
    )
    assert invited_user is None


def test_add_user_with_unitadmin(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps(first_new_user),
        content_type="application/json",
    )
    assert response.status == "200 OK"

    invited_user = (
        db.session.query(models.Invite).filter_by(email=first_new_user["email"]).one_or_none()
    )
    assert invited_user
    assert invited_user.email == first_new_user["email"]
    assert invited_user.role == first_new_user["role"]


def test_add_user_existing_email(client):
    invited_user = (
        db.session.query(models.Invite)
        .filter_by(email=existing_invite["email"], role=existing_invite["role"])
        .one_or_none()
    )
    assert invited_user
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps(existing_invite),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"


def test_add_user_with_unitpersonnel_permission_denied(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        data=json.dumps(new_unit_admin),
        content_type="application/json",
    )
    assert response.status == "403 FORBIDDEN"

    invited_user = (
        db.session.query(models.Invite).filter_by(email=new_unit_admin["email"]).one_or_none()
    )
    assert invited_user is None


def test_add_existing_user_without_project(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        data=json.dumps(existing_research_user),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"


def test_add_existing_user_to_existing_project(client):
    project = (
        db.session.query(models.Project)
        .filter_by(public_id=existing_research_user_to_existing_project["project"])
        .one_or_none()
    )
    user = (
        db.session.query(models.Email)
        .filter_by(email=existing_research_user_to_existing_project["email"])
        .one_or_none()
    )
    project_user_before_addition = (
        db.session.query(models.ProjectUsers)
        .filter(
            sqlalchemy.and_(
                models.ProjectUsers.user_id == user.user_id,
                models.ProjectUsers.project_id == project.id,
            )
        )
        .one_or_none()
    )
    assert project_user_before_addition is None
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        data=json.dumps(existing_research_user_to_existing_project),
        content_type="application/json",
    )
    assert response.status == "200 OK"

    project_user_after_addition = (
        db.session.query(models.ProjectUsers)
        .filter(
            sqlalchemy.and_(
                models.ProjectUsers.user_id == user.user_id,
                models.ProjectUsers.project_id == project.id,
            )
        )
        .one_or_none()
    )
    assert project_user_after_addition


def test_add_existing_user_to_nonexistent_proj(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        data=json.dumps(existing_research_user_to_nonexistent_proj),
        content_type="application/json",
    )
    assert response.status == "400 BAD REQUEST"


def test_existing_user_change_ownership(client):
    project = (
        db.session.query(models.Project)
        .filter_by(public_id=change_owner_existing_user["project"])
        .one_or_none()
    )
    user = (
        db.session.query(models.Email)
        .filter_by(email=change_owner_existing_user["email"])
        .one_or_none()
    )
    project_user = (
        db.session.query(models.ProjectUsers)
        .filter(
            sqlalchemy.and_(
                models.ProjectUsers.user_id == user.user_id,
                models.ProjectUsers.project_id == project.id,
            )
        )
        .one_or_none()
    )

    assert not project_user.owner

    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        data=json.dumps(change_owner_existing_user),
        content_type="application/json",
    )

    assert response.status == "200 OK"

    db.session.refresh(project_user)

    assert project_user.owner


def test_existing_user_change_ownership_same_permissions(client):
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        data=json.dumps(submit_with_same_ownership),
        content_type="application/json",
    )
    assert response.status == "403 FORBIDDEN"


def test_add_existing_user_with_unsuitable_role(client):
    user_with_unsuitable_role = existing_research_user_to_existing_project.copy()
    user_with_unsuitable_role["role"] = "Unit Admin"
    response = client.post(
        tests.DDSEndpoint.USER_ADD,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        data=json.dumps(user_with_unsuitable_role),
        content_type="application/json",
    )
    assert response.status == "403 FORBIDDEN"
