"""Authentication related functions/tools."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# built in libraries
import gc

# Installed
import datetime
import http
import flask
import json
import jwcrypto
from jwcrypto import jwk, jwt
import structlog

# Own modules
from dds_web import basic_auth, auth, mail
from dds_web.errors import AuthenticationError, AccessDeniedError, InviteError, TokenMissingError
from dds_web.database import models
import dds_web.utils

action_logger = structlog.getLogger("actions")

# VARIABLES ############################################################################ VARIABLES #

MFA_EXPIRES_IN = datetime.timedelta(hours=168)

####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################

# Error handler -------------------------------------------------------------------- Error handler #


@basic_auth.error_handler
def auth_error(status):
    """Handles 401 (Unauthorized) or 403 (Forbidden) for basic authentication."""
    return auth_error_common(status)


@auth.error_handler
def auth_error(status):
    """Handles 401 (Unauthorized) or 403 (Forbidden) for token authentication."""
    return auth_error_common(status)


def auth_error_common(status):
    """Checks if status code is 401 or 403 and raises appropriate exception."""
    if status == http.HTTPStatus.UNAUTHORIZED:
        raise AuthenticationError()
    elif status == http.HTTPStatus.FORBIDDEN:
        raise AccessDeniedError(message="Insufficient credentials")


# User roles -------------------------------------------------------------------------- User roles #


@basic_auth.get_user_roles
def get_user_roles(user):
    """Gets the role corresponding to the current user when basic authentication is used."""
    return get_user_roles_common(user)


@auth.get_user_roles
def get_user_roles(user):
    """Gets the role corresponding to the current user when token authentication is used."""
    return get_user_roles_common(user)


def get_user_roles_common(user):
    """Get the user role.

    If the user has Researcher role and a project, which the user has been set as an owner,
    has been specified, the user role is returned as Project Owner. Otherwise, it is Researcher.

    For all other users, return the value of the role set in the database table.
    """
    if user.role == "Researcher":
        request_args = flask.request.args
        project_public_id = request_args.get("project") if request_args else None
        if project_public_id:
            project = models.Project.query.filter_by(public_id=project_public_id).first()
            if project:
                project_user = models.ProjectUsers.query.filter_by(
                    project_id=project.id, user_id=user.username
                ).first()
                if project_user and project_user.owner:
                    return "Project Owner"
    return user.role


# Tokens ---------------------------------------------------------------------------------- Tokens #


def verify_token_no_data(token):
    """Verify token and return user row."""
    claims = __verify_general_token(token=token)
    user = __user_from_subject(subject=claims.get("sub"))
    # Clean up sensitive information
    del claims
    gc.collect()

    return user


def verify_password_reset_token(token):
    claims = __verify_general_token(token)
    user = __user_from_subject(claims.get("sub"))
    if user:
        rst = claims.get("rst")
        del claims
        gc.collect()
        if rst and rst == "pwd":
            return user
    raise AuthenticationError(message="Invalid token")


def verify_activate_totp_token(token, current_user):
    claims = __verify_general_token(token)
    user = __user_from_subject(claims.get("sub"))
    if user and (user == current_user):
        act = claims.get("act")
        del claims
        gc.collect()
        if act and act == "totp":
            return None
    raise AuthenticationError(message="Invalid token")


def __base_verify_token_for_invite(token):
    """Verify token and return claims."""
    claims = __verify_general_token(token=token)

    # Subject (user) not a valid entry
    if claims.get("sub"):
        raise AuthenticationError(message="Invalid token")

    return claims


def verify_invite_token(token):
    """Verify token sent in user invite."""
    claims = __base_verify_token_for_invite(token=token)

    # Email information required
    email = claims.get("inv")
    if not email:
        raise AuthenticationError(message="Invalid token")

    return email, models.Invite.query.filter(models.Invite.email == email).first()


def matching_email_with_invite(token, email):
    """Verify token and get email address."""
    claims = __base_verify_token_for_invite(token=token)
    return claims.get("inv") == email


def extract_token_invite_key(token):
    """Verify token, email and invite.

    Return invite and temporary key.
    """
    claims = __base_verify_token_for_invite(token=token)

    # Verify email in token
    email = claims.get("inv")
    if not email:
        raise AuthenticationError(message="Invalid token")

    # Verify that there's an invite for the current email
    invite = models.Invite.query.filter(models.Invite.email == email).first()
    if not invite:
        raise InviteError(message="Invite could not be found!")

    try:
        return invite, bytes.fromhex(claims.get("sen_con"))
    except ValueError as exc:
        raise ValueError(
            "Temporary key is expected be in hexadecimal digits for a byte string."
        ) from exc


def obtain_current_encrypted_token():
    try:
        return flask.request.headers["Authorization"].split()[1]
    except KeyError as exc:
        raise TokenMissingError("Encrypted token is required but missing!") from exc


def obtain_current_encrypted_token_claims():
    token = obtain_current_encrypted_token()
    if token:
        return decrypt_and_verify_token_signature(token)


@auth.verify_token
def verify_token(token):
    """Verify token used in token authentication."""
    claims = __verify_general_token(token=token)

    if claims.get("rst"):
        raise AuthenticationError(message="Invalid token")

    user = __user_from_subject(subject=claims.get("sub"))

    if user.password_reset:
        token_expired = claims.get("exp")
        token_issued = datetime.datetime.fromtimestamp(token_expired) - MFA_EXPIRES_IN
        password_reset_row = user.password_reset[0]
        if not password_reset_row.valid and password_reset_row.changed > token_issued:
            raise AuthenticationError(
                message=(
                    "Password reset performed after last authentication. "
                    "Start a new authenticated session to proceed."
                )
            )
    return __handle_multi_factor_authentication(
        user=user, mfa_auth_time_string=claims.get("mfa_auth_time")
    )


def __verify_general_token(token):
    """Verifies the format, signature and expiration time of an encrypted and signed JWT token.

    Raises AuthenticationError if token is invalid or absent, could raise other exceptions from
    dependencies. On successful verification, it returns a dictionary of the claims in the token.
    """
    # Token required
    if not token:
        raise AuthenticationError(message="No token")

    # Verify token signature if signed or decrypt first if encrypted
    try:
        data = (
            verify_token_signature(token=token)
            if token.count(".") == 2
            else decrypt_and_verify_token_signature(token=token)
        )
    except (ValueError, jwcrypto.common.JWException) as e:
        # ValueError is raised when the token doesn't look right (for example no periods)
        # jwcryopto.common.JWException is the base exception raised by jwcrypto,
        # and is raised when the token is malformed or invalid.
        flask.current_app.logger.exception(e)
        raise AuthenticationError(message="Invalid token") from e

    expiration_time = data.get("exp")
    # Use a hard check on top of the one from the dependency
    # exp shouldn't be before now no matter what
    if expiration_time and (
        dds_web.utils.current_time() <= datetime.datetime.fromtimestamp(expiration_time)
    ):
        return data

    raise AuthenticationError(message="Expired token")


def __user_from_subject(subject):
    """Get user row from username."""
    if subject:
        user = models.User.query.get(subject)
        if user:
            if not user.is_active:
                raise AccessDeniedError(
                    message=("Your account has been deactivated. You cannot use the DDS.")
                )
            return user


def __handle_multi_factor_authentication(user, mfa_auth_time_string):
    """Verify multifactor authentication time frame."""
    if user:
        if mfa_auth_time_string:
            mfa_auth_time = datetime.datetime.fromtimestamp(mfa_auth_time_string)
            if mfa_auth_time >= dds_web.utils.current_time() - MFA_EXPIRES_IN:
                return user

        if not user.totp_enabled:
            send_hotp_email(user)

        if flask.request.path.endswith("/user/second_factor"):
            return user

        raise AuthenticationError(
            message="Two-factor authentication is required! Please check your primary e-mail!"
        )


def send_hotp_email(user):
    """Send one time code via email."""
    # Only send if the hotp has not been issued or if it's been more than 15 minutes since
    # a hotp email was last sent
    if not user.hotp_issue_time or (
        user.hotp_issue_time
        and (dds_web.utils.current_time() - user.hotp_issue_time > datetime.timedelta(minutes=15))
    ):
        # Generate the one time code from the users specific hotp secret
        hotp_value = user.generate_HOTP_token()

        # Create and send email
        msg = dds_web.utils.create_one_time_password_email(user=user, hotp_value=hotp_value)
        mail.send(msg)
        return True
    return False


def extract_encrypted_token_sensitive_content(token, username):
    """Extract the sensitive content from inside the encrypted token."""
    if token is None:
        raise TokenMissingError(message="There is no token to extract sensitive content from.")
    content = decrypt_and_verify_token_signature(token=token)
    if content.get("sub") == username:
        return content.get("sen_con")


def decrypt_and_verify_token_signature(token):
    """Streamline decryption and signature verification and return the claims."""
    return verify_token_signature(token=decrypt_token(token=token))


def decrypt_token(token):
    """Decrypt the encrypted token.

    Return the signed token embedded inside.
    """
    # Get key used for encryption
    key = jwk.JWK.from_password(flask.current_app.config.get("SECRET_KEY"))
    # Decrypt token
    try:
        decrypted_token = jwt.JWT(key=key, jwt=token)
    except ValueError as exc:
        # "Token format unrecognized"
        raise AuthenticationError(message="Invalid token") from exc

    return decrypted_token.claims


def verify_token_signature(token):
    """Verify the signature of the token.

    Return the claims such as subject/username on valid signature.
    """
    # Get key used for signing
    key = jwk.JWK.from_password(flask.current_app.config.get("SECRET_KEY"))

    # Verify token
    try:
        jwttoken = jwt.JWT(key=key, jwt=token, algs=["HS256"])
        return json.loads(jwttoken.claims)
    except jwt.JWTExpired as exc:
        # jwt dependency uses a 60 seconds leeway to check exp
        # it also prints out a stack trace for it, so we handle it here
        raise AuthenticationError(message="Expired token") from exc
    except ValueError as exc:
        # "Token format unrecognized"
        raise AuthenticationError(message="Invalid token") from exc


@basic_auth.verify_password
def verify_password(username, password):
    """Verify that user exists and that password is correct."""
    user = models.User.query.get(username)

    if user and user.is_active and user.verify_password(input_password=password):
        send_hotp_email(user)
        return user
