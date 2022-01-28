import datetime

from dds_web.security.tokens import encrypted_jwt_token
from dds_web.security.auth import (
    extract_encrypted_token_content,
    decrypt_and_verify_token_signature,
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
