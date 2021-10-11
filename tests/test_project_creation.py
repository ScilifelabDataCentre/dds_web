# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import datetime
import json

# Own
from dds_web import db
from dds_web.database import models
import tests


# CONFIG #################################################################################### CONFIG #


proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}

# TESTS #################################################################################### TESTS #


def test_create_project_without_credentials(client):
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["researcher"]).post_headers(),
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    created_proj = (
        db.session.query(models.Project)
        .filter_by(
            created_by="username",
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
        headers=tests.UserAuth(tests.USER_CREDENTIALS["admin"]).post_headers(),
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    created_proj = (
        db.session.query(models.Project)
        .filter_by(
            created_by="admin",
            title=proj_data["title"],
            pi=proj_data["pi"],
            description=proj_data["description"],
        )
        .one_or_none()
    )
    assert created_proj and created_proj.date_created > time_before_run


def test_create_project_without_title_description(client):
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["admin"]).post_headers(),
        data=json.dumps({"pi": "piName"}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    created_proj = (
        db.session.query(models.Project)
        .filter_by(
            created_by="admin",
            pi=proj_data["pi"],
        )
        .one_or_none()
    )
    assert created_proj is None


def test_create_project_with_malformed_json(client):
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["admin"]).post_headers(),
        data="",
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    created_proj = (
        db.session.query(models.Project)
        .filter_by(
            created_by="admin",
            title="",
            pi="",
            description="",
        )
        .one_or_none()
    )
    assert created_proj is None


def test_create_project_by_user_with_no_unit(client):
    response = client.post(
        tests.DDSEndpoint.PROJECT_CREATE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["admin2"]).post_headers(),
        data=json.dumps(proj_data),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN
    created_proj = (
        db.session.query(models.Project)
        .filter_by(
            created_by="admin2",
            title=proj_data["title"],
            pi=proj_data["pi"],
            description=proj_data["description"],
        )
        .one_or_none()
    )
    assert created_proj is None
