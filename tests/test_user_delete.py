# Standard libraries
import flask
import http
import itsdangerous
import json
import pytest
import tests

# own modules
from dds_web import utils
from dds_web.database import models
import dds_web.api.errors as ddserr

# User deletion endpoints
# USER_DELETE = BASE_ENDPOINT + "/user/delete"
# USER_DELETE_SELF = BASE_ENDPOINT + "/user/delete_self"
# USER_CONFIRM_DELETE = "/confirm_deletion/"


#################################### UTILITY FUNCTIONS ##################################


def get_deletion_token(email):
    """Helper function to derive keys locally"""
    s = itsdangerous.URLSafeTimedSerializer(flask.current_app.config["SECRET_KEY"])
    token = s.dumps(email, salt="email-delete")
    return token


############################## INITIATE SELF-DELETION TESTS #############################


def test_del_self_nouser(client):
    """Request self deletion without user"""
    response = client.post(
        tests.DDSEndpoint.USER_DELETE_SELF,
        headers=None,
        data=None,
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED


def test_del_self(client):
    """Request self deletion."""
    response = client.post(
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


########################### CONFIRM SELF-DELETION ROUTE TESTS ###########################


def test_del_route_no_token(client):
    """Contact Route without token"""
    response = client.get(tests.DDSEndpoint.USER_CONFIRM_DELETE, content_type="application/json")
    assert response.status_code == http.HTTPStatus.NOT_FOUND


def test_del_route_invalid_token(client):
    """Use invalid signature"""


def test_del_route_expired_token(client):
    """Use expired token"""
    # "InJlc2VhcmNodXNlcjFAbWFpbHRyYXAuaW8i.YbIcrg.BmxUW6fKsnC3ujO5z1E_5CYiit4"


def test_del_route_valid_token(client):
    """Successfully request self deletion."""
    tests.UserAuth(tests.USER_CREDENTIALS["delete_me_researcher"]).login_web(client)


################################ FOREIGN DELETION TESTS #################################


def test_del_request_others_unprivileged(client):
    """Unprivileged deletion request"""

    email_to_delete = "delete_me_unitadmin@mailtrap.io"

    # with pytest.raises(ddserr.AccessDeniedError):
    response = client.post(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_unituser"]).token(client),
        data=json.dumps({"email": email_to_delete}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.FORBIDDEN

    # verify that user was not deleted
    exists = utils.email_return_user(email_to_delete)
    assert exists is not None
    assert type(exists).__name__ == "UnitUser"
    assert exists.primary_email == email_to_delete


def test_del_request_others_researcher(client):
    """Unit admin tries to delete research user"""

    email_to_delete = "researchuser@mailtrap.io"

    with pytest.raises(ddserr.UserDeletionError):
        response = client.post(
            tests.DDSEndpoint.USER_DELETE,
            headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_unitadmin"]).token(client),
            data=json.dumps({"email": email_to_delete}),
            content_type="application/json",
        )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # verify that user was not deleted
    exists = utils.email_return_user(email_to_delete)
    assert exists is not None
    assert type(exists).__name__ == "ResearchUser"
    assert exists.primary_email == email_to_delete


def test_del_request_others_researcher(client):
    """Unit admin tries to delete unit user from different unit"""

    email_to_delete = "unituser1@mailtrap.io"

    # with pytest.raises(ddserr.UserDeletionError):
    response = client.post(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_unitadmin"]).token(client),
        data=json.dumps({"email": email_to_delete}),
        content_type="application/json",
    )
    print(response.data)
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # verify that user was not deleted
    exists = utils.email_return_user(email_to_delete)
    assert exists is not None
    assert type(exists).__name__ == "UnitUser"
    assert exists.primary_email == email_to_delete


def test_del_request_others_self(client):
    """Unit admin tries to instantly self-delete via this endpoint"""

    email_to_delete = "delete_me_unitadmin@mailtrap.io"

    # with pytest.raises(ddserr.UserDeletionError):
    response = client.post(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_unitadmin"]).token(client),
        data=json.dumps({"email": email_to_delete}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST

    # verify that user was not deleted
    exists = utils.email_return_user(email_to_delete)
    assert exists is not None
    assert type(exists).__name__ == "UnitUser"
    assert exists.primary_email == email_to_delete


def test_del_request_others_success(client):
    """Unit admin deletes unit user"""

    email_to_delete = "delete_me_unituser@mailtrap.io"

    response = client.post(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["delete_me_unitadmin"]).token(client),
        data=json.dumps({"email": email_to_delete}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    # Make sure that user was deleted
    exists = utils.email_return_user(email_to_delete)
    assert exists is None


def test_del_request_others_superaction(client):
    """Super admin deletes unit admin"""

    email_to_delete = "delete_me_unitadmin@mailtrap.io"

    response = client.post(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["superadmin"]).token(client),
        data=json.dumps({"email": email_to_delete}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    # Make sure that user was deleted
    exists = utils.email_return_user(email_to_delete)
    assert exists is None
