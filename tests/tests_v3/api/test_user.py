"""Tests for user-related API endpoints (v3)."""

# IMPORTS #################################################

import logging
import tests
import http

# TESTS ###################################################

# EncryptedToken ############################################################# EncryptedToken #


def test_encrypted_token_without_authorization_header(client, caplog):
    """Calling the endpoint without auth header should return 401 and log warning."""
    # Call API without auth header
    with caplog.at_level(logging.WARNING):
        response = client.get(
            tests.DDSEndpoint.ENCRYPTED_TOKEN,
            headers=tests.DEFAULT_HEADER,
        )

    # Verify correct error message
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED
    assert "No authorization data provided." in caplog.text
    response_json = response.json
    assert response_json.get("message")
    assert "Missing or incorrect credentials" in response_json.get("message")
