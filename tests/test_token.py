import datetime

import pytest

from dds_web.errors import AuthenticationError
from dds_web.security.tokens import encrypted_jwt_token, jwt_token
from dds_web.security.auth import (
    extract_encrypted_token_content,
    decrypt_and_verify_token_signature,
    verify_invite_token,
    matching_email_with_invite,
    verify_token_no_data,
)


def test_encrypted_data_transfer_via_token(client):
    username = "researchuser"
    sensitive_content = "sensitive_content"
    encrypted_token = encrypted_jwt_token(username, sensitive_content)
    extracted_content = extract_encrypted_token_content(encrypted_token, username)
    assert sensitive_content == extracted_content


def test_encrypted_data_destined_for_another_user(client):
    encrypted_token = encrypted_jwt_token("researchuser", "sensitive_content")
    extracted_content = extract_encrypted_token_content(encrypted_token, "projectowner")
    assert extracted_content is None


def test_encrypted_and_signed_token(client):
    username = "researchuser"
    expires_in = datetime.timedelta(minutes=1)
    expiry_datetime = datetime.datetime.utcnow() + expires_in
    additional_claim = {"iss": "DDS"}
    encrypted_token = encrypted_jwt_token(
        username=username,
        sensitive_content=None,
        expires_in=expires_in,
        additional_claims=additional_claim,
    )
    token_content = decrypt_and_verify_token_signature(encrypted_token)
    assert username == token_content.get("sub")
    assert "DDS" == token_content.get("iss")

    token_expiry_datetime = datetime.datetime.fromtimestamp(token_content.get("exp"))
    assert token_expiry_datetime - expiry_datetime < datetime.timedelta(seconds=1)


def test_invalid_invite_token_with_a_sub(client):
    with pytest.raises(AuthenticationError) as error:
        verify_invite_token(
            encrypted_jwt_token(
                username="idontexist",
                sensitive_content="bogus",
                expires_in=datetime.timedelta(hours=1),
                additional_claims={"inv": "bogus.tkek@bogus.com"},
            )
        )
    assert "Invalid token" in str(error.value)


def test_invalid_invite_token_without_an_email(client):
    with pytest.raises(AuthenticationError) as error:
        verify_invite_token(
            encrypted_jwt_token(
                username="",
                sensitive_content="bogus",
                expires_in=datetime.timedelta(hours=1),
            )
        )
    assert "Invalid token" in str(error.value)


def test_valid_invite_token(client):
    email, invite_row = verify_invite_token(
        encrypted_jwt_token(
            username="",
            sensitive_content="bogus",
            expires_in=datetime.timedelta(hours=24),
            additional_claims={"inv": "existing_invite_email@mailtrap.io"},
        )
    )
    assert email == "existing_invite_email@mailtrap.io"
    assert invite_row
    assert invite_row.email == "existing_invite_email@mailtrap.io"


def test_valid_invite_token_with_absent_invite(client):
    email, invite_row = verify_invite_token(
        encrypted_jwt_token(
            username="",
            sensitive_content="bogus",
            expires_in=datetime.timedelta(hours=24),
            additional_claims={"inv": "bogus.tkek@bogus.com"},
        )
    )
    assert email == "bogus.tkek@bogus.com"
    assert not invite_row


def test_nonmatching_form_email_with_invite_token(client):
    assert (
        matching_email_with_invite(
            encrypted_jwt_token(
                username="",
                sensitive_content="bogus",
                expires_in=datetime.timedelta(hours=24),
                additional_claims={"inv": "existing_invite_email@mailtrap.io"},
            ),
            "bogus.tkek@bogus.com",
        )
        is False
    )


def test_matching_form_email_with_invite_token(client):
    assert (
        matching_email_with_invite(
            encrypted_jwt_token(
                username="",
                sensitive_content="bogus",
                expires_in=datetime.timedelta(hours=24),
                additional_claims={"inv": "existing_invite_email@mailtrap.io"},
            ),
            "existing_invite_email@mailtrap.io",
        )
        is True
    )


def test_verify_token_no_data(client):
    assert (
        verify_token_no_data(encrypted_jwt_token(username="idontexist", sensitive_content=None))
        is None
    )
    assert verify_token_no_data(jwt_token(username="idontexist")) is None

    assert verify_token_no_data(encrypted_jwt_token(username="", sensitive_content=None)) is None
    assert verify_token_no_data(jwt_token(username="")) is None

    user = verify_token_no_data(encrypted_jwt_token(username="unitadmin", sensitive_content=None))
    assert user.username == "unitadmin"
    user = verify_token_no_data(jwt_token(username="unitadmin"))
    assert user.username == "unitadmin"
