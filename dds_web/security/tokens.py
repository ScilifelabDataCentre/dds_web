####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import datetime
import secrets

# Installed
import flask
from jwcrypto import jwk, jwt

# Own modules
import dds_web.utils
import dds_web.forms


# Functions ############################################################################ FUNCTIONS #
def encrypted_jwt_token(
    username,
    sensitive_content,
    expires_in=datetime.timedelta(hours=168),
    additional_claims=None,
    fully_authenticated=False,
):
    """
    Encrypts a signed JWT token. This is to be used for any encrypted token regardless of the sensitive content.

    :param str username: Username must be obtained through authentication
    :param str or None sensitive_content: This is the content that must be protected by encryption.
        Can be set to None for protecting the signed token.
    :param timedelta expires_in: This is the maximum allowed age of the token. (default 2 days)
    :param Dict or None additional_claims: Any additional token claims can be added. e.g., {"iss": "DDS"}
    :param Boolean fully_authenticated: set to True only after successful 2fa which means that all authentication
        steps have succeeded and this final token can be used for normal operation by the cli (default False)
    """
    jwe_protected_header = {
        "alg": "A256KW",
        "enc": "A256GCM",
    }
    if fully_authenticated:
        # exp claim in this (integrity) protected JWE header is provided only to let the
        # cli know the precise expiration time of the encrypted token. It has no impact
        # on the actual enforcement of the expiration of the token.
        # This time is in iso format in contrast to the actual exp claim in timestamp,
        # because timestamp translates to a wrong time in local date time
        jwe_protected_header["exp"] = (dds_web.utils.current_time() + expires_in).isoformat()

    token = jwt.JWT(
        header=jwe_protected_header,
        claims=__signed_jwt_token(
            username=username,
            sensitive_content=sensitive_content,
            expires_in=expires_in,
            additional_claims=additional_claims,
        ),
    )
    key = jwk.JWK.from_password(flask.current_app.config.get("SECRET_KEY"))
    token.make_encrypted_token(key)
    return token.serialize()


def update_token_with_mfa(token_claims):
    expires_in = (
        datetime.datetime.fromtimestamp(token_claims.get("exp")) - dds_web.utils.current_time()
    )
    return encrypted_jwt_token(
        username=token_claims.get("sub"),
        sensitive_content=token_claims.get("sen_con"),
        expires_in=expires_in,
        additional_claims={"mfa_auth_time": dds_web.utils.current_time().timestamp()},
        fully_authenticated=True,
    )


def __signed_jwt_token(
    username,
    sensitive_content=None,
    expires_in=datetime.timedelta(hours=168),
    additional_claims=None,
):
    """
    Generic signed JWT token. This is to be used by both signed-only and signed-encrypted tokens.

    :param str username: Username must be obtained through authentication
    :param str or None sensitive_content: This is the content that must be protected by encryption. (default None)
    :param timedelta expires_in: This is the maximum allowed age of the token. (default 2 days)
    :param Dict or None additional_claims: Any additional token claims can be added. e.g., {"iss": "DDS"}
    """
    expiration_time = dds_web.utils.current_time() + expires_in

    # exp claim has to be in timestamp, otherwise jwcrypto cannot verify the exp claim
    # and so raises an exception for it. This does not cause any timezone issues as it
    # is only issued and verified on the api side.
    data = {"sub": username, "exp": expiration_time.timestamp(), "nonce": secrets.token_hex(32)}
    if additional_claims:
        data.update(additional_claims)
    if sensitive_content:
        data["sen_con"] = sensitive_content

    key = jwk.JWK.from_password(flask.current_app.config.get("SECRET_KEY"))
    token = jwt.JWT(header={"alg": "HS256"}, claims=data, algs=["HS256"])
    token.make_signed_token(key)
    return token.serialize()


def jwt_token(username, expires_in=datetime.timedelta(hours=168), additional_claims=None):
    """
    Generates a signed JWT token. This is to be used for general purpose signed token.
    :param str username: Username must be obtained through authentication
    :param timedelta expires_in: This is the maximum allowed age of the token. (default 2 days)
    :param Dict or None additional_claims: Any additional token claims can be added. e.g., {"iss": "DDS"}
    """
    return __signed_jwt_token(
        username=username, expires_in=expires_in, additional_claims=additional_claims
    )
