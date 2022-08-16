"""Testing of the dds_web code with pytest."""

from base64 import b64encode
import dds_web.errors as ddserr
import dds_web.database
import flask
import flask_login
from requests_mock.mocker import Mocker
from dds_web.version import __version__
from typing import Dict

# Copied from dds_cli __init__.py:

__all__ = [
    "USER_CREDENTIALS",
    "UserAuth",
    "DDSEndpoint",
]


###############################################################################
# VARIABLES ####################################################### VARIABLES #
###############################################################################

# The credentials used for the tests
USER_CREDENTIALS = {
    "empty": ":",
    "nouser": ":password",
    "nopassword": "username:",
    "wronguser": "scriptkiddie:password",
    "wrongpassword": "researchuser:wrongpassword",
    "researcher": "researchuser:password",
    "researchuser": "researchuser:password",
    "researchuser2": "researchuser2:password",
    "projectowner": "projectowner:password",
    "unituser": "unituser:password",
    "unitadmin": "unitadmin:password",
    "superadmin": "superadmin:password",
    "delete_me_researcher": "delete_me_researcher:password",
    "delete_me_unituser": "delete_me_unituser:password",
    "delete_me_unitadmin": "delete_me_unitadmin:password",
}

DEFAULT_HEADER = {"X-CLI-Version": __version__}

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################
class UserAuth:
    """A helper class that can return the credentials in various forms as required for the API."""

    def __init__(self, credentials):
        self.credentials = credentials

    # class can be extended by various means to act on the credentials

    def plain(self):
        return self.credentials

    def as_tuple(self):
        return tuple(self.credentials.split(":"))

    def basic(self):
        return b64encode(self.credentials.encode("utf-8")).decode("utf-8")

    def post_headers(self):
        return {
            "Authorization": f"Basic {self.basic()}",
            "Cache-Control": "no-cache",
            **DEFAULT_HEADER,
        }

    def fetch_hotp(self):
        user = dds_web.database.models.User.query.filter_by(username=self.username).first()
        return user.generate_HOTP_token()

    def partial_token(self, client):
        """Return a partial token that can be used to get a full token."""
        headers: Dict = {"Cache-Control": "no-cache", **DEFAULT_HEADER}
        response = client.get(DDSEndpoint.ENCRYPTED_TOKEN, headers=headers, auth=(self.as_tuple()))

        # Get response from api
        response_json = response.json
        token = response_json["token"]

        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
            return headers

    def token(self, client):
        with Mocker() as mock:
            temp_token = self.partial_token(client)

            hotp_token = self.fetch_hotp()

            response = client.get(
                DDSEndpoint.SECOND_FACTOR,
                headers=temp_token,
                json={"HOTP": hotp_token.decode()},
            )

            response_json = response.json
            token = response_json["token"]
            if token is not None:
                return {
                    "Authorization": f"Bearer {token}",
                    "Cache-Control": "no-cache",
                    **DEFAULT_HEADER,
                }
            else:
                raise ddserr.JwtTokenGenerationError()

    @property
    def username(self):
        return self.as_tuple()[0]

    def fake_web_login(self, client):
        from flask import session

        user = dds_web.database.models.User.query.filter_by(username=self.username).first()

        def set_session_cookie(client):
            app = flask.current_app
            val = app.session_interface.get_signing_serializer(app).dumps(dict(session))
            client.set_cookie("localhost", app.session_cookie_name, val)

        flask_login.login_user(user)
        set_session_cookie(client)

        return client


class DDSEndpoint:
    """Defines all DDS urls."""

    # Base url - local or remote
    BASE_ENDPOINT = "/api/v1"

    # status
    STATUS = "/status"

    # Web
    INDEX = "/"
    POLICY="/policy"
    TROUBLE = "/trouble"
    LOGIN = "/login"
    LOGOUT = "/logout"
    CANCEL_2FA = "/cancel_2fa"
    CONFIRM_2FA = "/confirm_2fa"
    CHANGE_PASSWORD = "/change_password"

    # User creation
    USER_ADD = BASE_ENDPOINT + "/user/add"
    USER_CONFIRM = "/confirm_invite/"
    USER_NEW = "/register"
    REQUEST_RESET_PASSWORD = "/reset_password"
    RESET_PASSWORD = "/reset_password/"
    PASSWORD_RESET_COMPLETED = "/password_reset_completed"
    ACTIVATE_HOTP_WEB = "/activate_hotp/"
    ACTIVATE_TOTP_WEB = "/activate_totp/"

    # User INFO
    USER_INFO = BASE_ENDPOINT + "/user/info"

    # User deletion
    USER_DELETE = BASE_ENDPOINT + "/user/delete"
    USER_DELETE_SELF = BASE_ENDPOINT + "/user/delete_self"
    USER_CONFIRM_DELETE = "/confirm_deletion/"

    # List users
    LIST_USERS = BASE_ENDPOINT + "/users"

    # Authentication - user and project
    ENCRYPTED_TOKEN = BASE_ENDPOINT + "/user/encrypted_token"
    SECOND_FACTOR = BASE_ENDPOINT + "/user/second_factor"

    # Remove user from project
    REMOVE_USER_FROM_PROJ = BASE_ENDPOINT + "/user/access/revoke"

    # User activation
    USER_ACTIVATION = BASE_ENDPOINT + "/user/activation"

    # Switching authentication methods
    TOTP_ACTIVATION = BASE_ENDPOINT + "/user/totp/activate"
    HOTP_ACTIVATION = BASE_ENDPOINT + "/user/hotp/activate"

    # S3Connector keys
    S3KEYS = BASE_ENDPOINT + "/s3/proj"

    # File related urls
    FILE_NEW = BASE_ENDPOINT + "/file/new"
    FILE_MATCH = BASE_ENDPOINT + "/file/match"
    FILE_INFO = BASE_ENDPOINT + "/file/info"
    FILE_INFO_ALL = BASE_ENDPOINT + "/file/all/info"
    FILE_UPDATE = BASE_ENDPOINT + "/file/update"

    # Project specific urls
    PROJECT_CREATE = BASE_ENDPOINT + "/proj/create"
    PROJECT_STATUS = BASE_ENDPOINT + "/proj/status"
    PROJECT_ACCESS = BASE_ENDPOINT + "/proj/access"

    # Listing urls
    LIST_PROJ = BASE_ENDPOINT + "/proj/list"
    LIST_FILES = BASE_ENDPOINT + "/files/list"
    LIST_PROJ_USERS = BASE_ENDPOINT + "/proj/users"

    # Deleting urls
    REMOVE_PROJ_CONT = BASE_ENDPOINT + "/proj/rm"
    REMOVE_FILE = BASE_ENDPOINT + "/file/rm"
    REMOVE_FOLDER = BASE_ENDPOINT + "/file/rmdir"

    # Encryption keys
    PROJ_PUBLIC = BASE_ENDPOINT + "/proj/public"
    PROJ_PRIVATE = BASE_ENDPOINT + "/proj/private"

    # Display unit usage
    USAGE = BASE_ENDPOINT + "/usage"
    INVOICE = BASE_ENDPOINT + "/invoice"

    # Superadmins only
    LIST_UNITS_ALL = BASE_ENDPOINT + "/unit/info/all"
    MOTD = BASE_ENDPOINT + "/motd"
    USER_FIND = BASE_ENDPOINT + "/user/find"

    TIMEOUT = 5
