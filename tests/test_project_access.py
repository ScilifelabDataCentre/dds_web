# IMPORTS ################################################################################ IMPORTS #

# Standard library
import http
import json
import pytest
import marshmallow
import unittest

# Own
from dds_web import db
from dds_web.database import models
import tests


# CONFIG ################################################################################## CONFIG #

# proj_data = {"pi": "piName", "title": "Test proj", "description": "A longer project description"}
proj_query = {"project": "public_project_id"}
# proj_query_restricted = {"project": "restricted_project_id"}

# TESTS #################################################################################### TESTS #


def test_fix_access_no_token(client):
    """Token required to fix project access."""
    response = client.post(tests.DDSEndpoint.PROJECT_ACCESS)
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
