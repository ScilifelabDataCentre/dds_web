# """Tests for authentication-related functionality."""

# # IMPORTS #################################################

# import pytest
# import logging
# import http

# import tests

# # TESTS ###################################################


# # Run test three times with different missing credentials scenarios
# @pytest.mark.parametrize("credentials_key", ["nouser", "nopassword", "empty"])
# def test_auth_missing_credentials_logs_warning(client, caplog, credentials_key):
#     """Missing credentials should log warning and return 401."""

#     with caplog.at_level(logging.WARNING):
#         # Call API with missing credentials
#         response = client.get(
#             tests.DDSEndpoint.ENCRYPTED_TOKEN,
#             auth=tests.UserAuth(tests.USER_CREDENTIALS[credentials_key]).as_tuple(),
#             headers=tests.DEFAULT_HEADER,
#         )

#     # Verify correct error message
#     assert response.status_code == http.HTTPStatus.UNAUTHORIZED
#     response_json = response.json
#     assert response_json.get("message")
#     assert "Missing or incorrect credentials" == response_json.get("message")
#     assert (
#         "No username or password provided. Something wrong. This shouldn't happen." in caplog.text
#     )
