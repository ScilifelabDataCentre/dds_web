# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import datetime
import json
import unittest

# Own
from dds_web import db
from dds_web.database import models
import tests


# CONFIG ################################################################################## CONFIG #

proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}
proj_data_with_existing_users = {
    **proj_data,
    "users_to_add": [
        {"email": "researchuser@mailtrap.io", "role": "Researcher", "owner": True},
        {"email": "researchuser2@mailtrap.io", "role": "Researcher"},
    ],
}

# TESTS #################################################################################### TESTS #


def test_create_project_without_credentials(client):
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researchuser"]).post_headers(),
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    created_proj = (
        db.session.query(models.Project)
        .filter_by(
            created_by="researchuser",
            title=proj_data["title"],
            pi=proj_data["pi"],
            description=proj_data["description"],
        )
        .one_or_none()
    )
    assert created_proj is None


def test_create_project_with_credentials(client):
    time_before_run = datetime.datetime.now()
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).post_headers(),
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    created_proj = (
        db.session.query(models.Project)
        .filter_by(
            created_by="unituser",
            title=proj_data["title"],
            pi=proj_data["pi"],
            description=proj_data["description"],
        )
        .one_or_none()
    )
    assert (
        created_proj
        and created_proj.date_created > time_before_run
        and not created_proj.is_sensitive
    )


def test_create_project_without_title_description(client):
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).post_headers(),
        data=json.dumps({"pi": "piName"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    created_proj = (
        db.session.query(models.Project)
        .filter_by(
            created_by="unituser",
            pi=proj_data["pi"],
        )
        .one_or_none()
    )
    assert created_proj is None


def test_create_project_with_malformed_json(client):
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).post_headers(),
        data="",
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    created_proj = (
        db.session.query(models.Project)
        .filter_by(
            created_by="unituser",
            title="",
            pi="",
            description="",
        )
        .one_or_none()
    )
    assert created_proj is None


def test_create_project_sensitive(client):
    p_data = proj_data
    p_data["is_sensitive"] = True
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).post_headers(),
        data=json.dumps(p_data),
        content_type="application/json",
    )
    assert response.status == "200 OK"
    created_proj = (
        db.session.query(models.Project)
        .filter_by(
            created_by="unituser",
            title=proj_data["title"],
            pi=proj_data["pi"],
            description=proj_data["description"],
        )
        .one_or_none()
    )
    assert created_proj and created_proj.is_sensitive


def test_create_project_with_users(client):
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).post_headers(),
        data=json.dumps(proj_data_with_existing_users),
        content_type="application/json",
    )
    assert response.status == "200 OK"
    resp_json = response.json
    created_proj = (
        db.session.query(models.Project).filter_by(public_id=resp_json["project_id"]).one_or_none()
    )
    assert created_proj
    users = db.session.query(models.ProjectUsers).filter_by(project_id=created_proj.id).all()
    users_dict_from_db = []

    for user in users:
        users_dict_from_db.append({"username": user.user_id, "owner": user.owner})

    users_dict_from_email = []
    for user in proj_data_with_existing_users["users_to_add"]:
        email = db.session.query(models.Email).filter_by(email=user["email"]).one_or_none()
        users_dict_from_email.append({"username": email.user_id, "owner": user.get("owner", False)})

    case = unittest.TestCase()
    case.assertCountEqual(users_dict_from_db, users_dict_from_email)
