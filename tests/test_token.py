import datetime

import flask
import pytest
from jwcrypto import jwt

import dds_web.utils
import tests
from dds_web.errors import AuthenticationError, TokenMissingError, InviteError
from dds_web.security.tokens import encrypted_jwt_token, jwt_token
from dds_web.security.auth import (
    extract_encrypted_token_sensitive_content,
    decrypt_and_verify_token_signature,
    verify_invite_token,
    matching_email_with_invite,
    verify_token_no_data,
    extract_token_invite_key,
    obtain_current_encrypted_token,
    obtain_current_encrypted_token_claims,
    verify_token,
)


def test_encrypted_data_transfer_via_token(client):
    username = "researchuser"
    sensitive_content = "sensitive_content"
    encrypted_token = encrypted_jwt_token(username=username, sensitive_content=sensitive_content)
    extracted_content = extract_encrypted_token_sensitive_content(encrypted_token, username)
    assert sensitive_content == extracted_content


def test_encrypted_data_destined_for_another_user(client):
    encrypted_token = encrypted_jwt_token(
        username="researchuser", sensitive_content="sensitive_content"
    )
    extracted_content = extract_encrypted_token_sensitive_content(encrypted_token, "projectowner")
    assert extracted_content is None


def test_extract_encrypted_token_sensitive_content_no_token(client):
    with pytest.raises(TokenMissingError) as error:
        extract_encrypted_token_sensitive_content(None, "projectowner")
    assert "There is no token to extract sensitive content from." in str(error.value)


def test_encrypted_and_signed_token(client):
    username = "researchuser"
    expires_in = datetime.timedelta(minutes=1)
    expiry_datetime = dds_web.utils.current_time() + expires_in
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


def test_extract_token_invite_key_with_wrong_token(client):
    with pytest.raises(AuthenticationError) as error:
        extract_token_invite_key(encrypted_jwt_token(username="unitadmin", sensitive_content=None))
    assert "Invalid token" in str(error.value)


def test_extract_token_invite_key_with_no_invite(client):
    with pytest.raises(InviteError) as error:
        extract_token_invite_key(
            encrypted_jwt_token(
                username="",
                sensitive_content="bogus",
                expires_in=datetime.timedelta(hours=24),
                additional_claims={"inv": "bogus.tkek@bogus.com"},
            )
        )
    assert "Invite could not be found!" in str(error.value)


def test_extract_token_invite_key_with_wrong_format_for_key(client):
    with pytest.raises(ValueError) as error:
        extract_token_invite_key(
            encrypted_jwt_token(
                username="",
                sensitive_content="bogus",
                expires_in=datetime.timedelta(hours=24),
                additional_claims={"inv": "existing_invite_email@mailtrap.io"},
            )
        )
    assert "Temporary key is expected be in hexadecimal digits for a byte string." in str(
        error.value
    )


def test_extract_token_invite_key_successful(client):
    invite, temporary_key = extract_token_invite_key(
        encrypted_jwt_token(
            username="",
            sensitive_content=b"bogus".hex(),
            expires_in=datetime.timedelta(hours=24),
            additional_claims={"inv": "existing_invite_email@mailtrap.io"},
        )
    )
    assert invite
    assert invite.email == "existing_invite_email@mailtrap.io"
    assert temporary_key == b"bogus"


def test_obtain_current_encrypted_token_fails(client):
    with pytest.raises(TokenMissingError) as error:
        obtain_current_encrypted_token()

    assert "Encrypted token is required but missing!" in str(error.value)


def test_fully_authenticated_encrypted_token_protected_header(client):
    before_token_issue = dds_web.utils.current_time()
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    after_token_issue = dds_web.utils.current_time()

    # token here is a dict
    token = token["Authorization"].split()[1]

    # token here becomes a jwt by deserializing from raw token string
    token = jwt.JWT(jwt=token)

    # now we access the jose header, which includes the integrity protected header
    # and check what should be and not be there
    assert token.token.jose_header["alg"] == "A256KW"
    assert token.token.jose_header["enc"] == "A256GCM"

    assert "iat" not in token.token.jose_header
    assert "sub" not in token.token.jose_header
    assert "sen_con" not in token.token.jose_header

    # this exp is used for the cli, it is not the actual exp because that is
    # encrypted in the token. We have not decrypted the token yet, just
    # deserialized it. Jose header is visible in plaintext.
    assert "exp" in token.token.jose_header
    expiration_time = datetime.datetime.fromisoformat(token.token.jose_header["exp"])
    token_issue = expiration_time - datetime.timedelta(hours=168)
    assert before_token_issue < token_issue
    assert after_token_issue > token_issue


def test_exp_for_cli_not_in_protected_header_of_invite_token(client):
    token = encrypted_jwt_token(
        username="",
        sensitive_content=b"bogus".hex(),
        expires_in=datetime.timedelta(
            hours=flask.current_app.config["INVITATION_EXPIRES_IN_HOURS"]
        ),
        additional_claims={"inv": "bogus.email@bogus.com"},
    )
    token = jwt.JWT(jwt=token)
    assert "exp" not in token.token.jose_header


def test_exp_for_cli_not_in_protected_header_of_reset_password_token(client):
    token = encrypted_jwt_token(
        username="unitadmin",
        sensitive_content=None,
        expires_in=datetime.timedelta(
            seconds=3600,
        ),
        additional_claims={"rst": "pwd"},
    )
    token = jwt.JWT(jwt=token)
    assert "exp" not in token.token.jose_header


def test_exp_for_cli_not_in_protected_header_of_partial_token(client):
    token = encrypted_jwt_token(username="unitadmin", sensitive_content=None)
    token = jwt.JWT(jwt=token)
    assert "exp" not in token.token.jose_header


def test_obtain_current_encrypted_token_succeeds(client):
    initial_token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)

    # Use an endpoint to put the token in the request header.
    client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        query_string={"project": "restricted_project_id"},
        headers=initial_token,
    )

    obtained_token = obtain_current_encrypted_token()
    assert str(initial_token["Authorization"].split()[1]) == str(obtained_token)


def test_obtain_current_encrypted_token_claims(client):
    initial_token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)

    # Use an endpoint to put the token in the request header.
    client.get(
        tests.DDSEndpoint.PROJ_PUBLIC,
        query_string={"project": "restricted_project_id"},
        headers=initial_token,
    )

    obtained_token_claims = obtain_current_encrypted_token_claims()
    assert obtained_token_claims.get("sub") == "unitadmin"


def test_expired_encrypted_token(client):
    token = encrypted_jwt_token(
        username="researchuser", sensitive_content=None, expires_in=datetime.timedelta(seconds=-2)
    )
    with pytest.raises(AuthenticationError) as error:
        verify_token(token)

    assert "Expired token" in str(error.value)
