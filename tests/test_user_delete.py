# Standard libraries
import http

# Installed
import flask
import itsdangerous
import json
import pytest

# own modules
from dds_web import db
from dds_web.database import models

import dds_web.utils
import dds_web.errors as ddserr
import tests


#################################### UTILITY FUNCTIONS ##################################


def get_deletion_token(email):
    """Helper function to derive keys locally"""
    s = itsdangerous.URLSafeTimedSerializer(flask.current_app.config["SECRET_KEY"])
    token = s.dumps(email, salt="email-delete")
    return token


def user_from_email(email):
    """Helper function to return the User for a given email"""
    user = models.User.query.join(models.Email).filter(models.Email.email == email).one_or_none()
    return user


def create_delete_request(email_str):
    user = user_from_email(email_str)
    new_delrequest = models.DeletionRequest(
        **{
            "requester": user,
            "email": email_str,
            "issued": dds_web.utils.current_time(),
        }
    )
    db.session.add(new_delrequest)
    db.session.commit()


############################## INITIATE SELF-DELETION TESTS #############################


def test_del_self_nouser(client):
    """Request self deletion without user"""
    response = client.delete(
        tests.DDSEndpoint.USER_DELETE_SELF,
        headers=None,
        data=None,
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED


def test_del_self(client):
    """Request self deletion."""
    response = client.delete(
        tests.DDSEndpoint.USER_DELETE_SELF,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_researcher"]).token(client),
        data=None,
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    # assert creation of deletion request
    del_req = models.DeletionRequest.query.filter_by(
        email="delete_me_researcher@mailtrap.io"
    ).one_or_none()

    assert del_req is not None

    response = client.delete(
        tests.DDSEndpoint.USER_DELETE_SELF,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_researcher"]).token(client),
        data=None,
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK
    assert (
        "The confirmation link has already been sent to your address delete_me_researcher@mailtrap.io!"
        in response.json["message"]
    )


########################### CONFIRM SELF-DELETION ROUTE TESTS ###########################


def test_del_route_no_token(client):
    """Contact Route without token"""
    response = client.get(tests.DDSEndpoint.USER_CONFIRM_DELETE, content_type="application/json")
    assert response.status_code == http.HTTPStatus.NOT_FOUND


def test_del_route_invalid_token(client):
    """Use invalid signature"""
    client = tests.UserAuth(tests.USER_CREDENTIALS["delete_me_researcher"]).fake_web_login(client)

    response = client.get(
        tests.DDSEndpoint.USER_CONFIRM_DELETE + "invalidtoken", content_type="application/json"
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST


def test_del_route_expired_token(client):
    """Use expired token"""
    token = "InJlc2VhcmNodXNlcjFAbWFpbHRyYXAuaW8i.YbIcrg.BmxUW6fKsnC3ujO5z1E_5CYiit4"
    client = tests.UserAuth(tests.USER_CREDENTIALS["delete_me_researcher"]).fake_web_login(client)

    response = client.get(
        tests.DDSEndpoint.USER_CONFIRM_DELETE + token, content_type="application/json"
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST


def test_del_route_valid_token_wrong_user(client):
    """Confirm self deletion but using the wrong login."""
    email_to_delete = "delete_me_researcher@mailtrap.io"
    create_delete_request(email_to_delete)
    token = get_deletion_token(email_to_delete)

    # Use wrong login here
    client = tests.UserAuth(tests.USER_CREDENTIALS["researchuser2"]).fake_web_login(client)

    response = client.get(
        tests.DDSEndpoint.USER_CONFIRM_DELETE + token, content_type="application/json"
    )

    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    exists = user_from_email(email_to_delete)
    assert exists is not None


def test_del_route_valid_token(client):
    """Successfully request self deletion."""
    email_to_delete = "delete_me_researcher@mailtrap.io"
    create_delete_request(email_to_delete)
    token = get_deletion_token(email_to_delete)

    client = tests.UserAuth(tests.USER_CREDENTIALS["delete_me_researcher"]).fake_web_login(client)

    response = client.get(
        tests.DDSEndpoint.USER_CONFIRM_DELETE + token, content_type="application/json"
    )

    assert response.status_code == http.HTTPStatus.OK

    exists = user_from_email(email_to_delete)
    assert exists is None

    # Check for email existence as well


################################ FOREIGN DELETION TESTS #################################


def test_del_request_others_unprivileged(client):
    """Unprivileged deletion request"""

    email_to_delete = "delete_me_unitadmin@mailtrap.io"

    # with pytest.raises(ddserr.AccessDeniedError):
    response = client.delete(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_unituser"]).token(client),
        data=json.dumps({"email": email_to_delete}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # verify that user was not deleted
    exists = user_from_email(email_to_delete)
    assert exists is not None
    assert type(exists).__name__ == "UnitUser"
    assert exists.primary_email == email_to_delete


def test_del_request_others_researcher(client):
    """Unit admin tries to delete research user"""

    email_to_delete = "researchuser@mailtrap.io"

    with pytest.raises(ddserr.UserDeletionError):
        response = client.delete(
            tests.DDSEndpoint.USER_DELETE,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_unitadmin"]).token(client),
            data=json.dumps({"email": email_to_delete}),
            content_type="application/json",
        )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # verify that user was not deleted
    exists = user_from_email(email_to_delete)
    assert exists is not None
    assert type(exists).__name__ == "ResearchUser"
    assert exists.primary_email == email_to_delete


def test_del_request_others_researcher(client):
    """Unit admin tries to delete unit user from different unit"""

    email_to_delete = "unituser1@mailtrap.io"

    # with pytest.raises(ddserr.UserDeletionError):
    response = client.delete(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_unitadmin"]).token(client),
        data=json.dumps({"email": email_to_delete}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # verify that user was not deleted
    exists = user_from_email(email_to_delete)
    assert exists is not None
    assert type(exists).__name__ == "UnitUser"
    assert exists.primary_email == email_to_delete


def test_del_request_others_self(client):
    """Unit admin tries to instantly self-delete via this endpoint"""

    email_to_delete = "delete_me_unitadmin@mailtrap.io"

    # with pytest.raises(ddserr.UserDeletionError):
    response = client.delete(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_unitadmin"]).token(client),
        data=json.dumps({"email": email_to_delete}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # verify that user was not deleted
    exists = user_from_email(email_to_delete)
    assert exists is not None
    assert type(exists).__name__ == "UnitUser"
    assert exists.primary_email == email_to_delete


def test_del_request_others_success(client):
    """Unit admin deletes unit user"""

    email_to_delete = "delete_me_unituser@mailtrap.io"

    response = client.delete(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_unitadmin"]).token(client),
        data=json.dumps({"email": email_to_delete}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    # Make sure that user was deleted
    exists = user_from_email(email_to_delete)
    assert exists is None
    assert dds_web.utils.email_in_db(email_to_delete) is False


def test_del_request_others_superaction(client):
    """Super admin deletes unit admin"""

    email_to_delete = "delete_me_unitadmin@mailtrap.io"

    response = client.delete(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
        data=json.dumps({"email": email_to_delete}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    # Make sure that user was deleted
    exists = user_from_email(email_to_delete)
    assert exists is None
    assert dds_web.utils.email_in_db(email_to_delete) is False
