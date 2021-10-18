import base64

from dds_web.api.user import encrypted_jwt_token
from dds_web.security.auth import extract_encrypted_token_content


def test_encrypted_data_transfer_via_token(client):
    username = "researchuser"
    sensitive_content = "sensitive_content"
    encrypted_token = encrypted_jwt_token(username, sensitive_content)
    decoded_encrypted_token = base64.b64decode(encrypted_token + b"==")
    assert "sensitive_content" not in decoded_encrypted_token

    extracted_content = extract_encrypted_token_content(encrypted_token, username)
    assert sensitive_content == extracted_content


def test_encrypted_data_destined_for_another_user(client):
    encrypted_token = encrypted_jwt_token("researchuser", "sensitive_content")
    extracted_content = extract_encrypted_token_content(encrypted_token, "projectowner")
    assert extracted_content is None
