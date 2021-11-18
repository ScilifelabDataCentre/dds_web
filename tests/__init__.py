"""Testing of the dds_web code with pytest."""

from base64 import b64encode
import dds_web.api.errors as ddserr

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
    "researcher": "researchuser:password",
    "researchuser": "researchuser:password",
    "researchuser2": "researchuser2:password",
    "projectowner": "projectowner:password",
    "unituser": "unituser:password",
    "unitadmin": "unitadmin:password",
    "superadmin": "superadmin:password",
}

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
        return {"Authorization": f"Basic {self.basic()}"}

    def token(self, client):

        response = client.get(DDSEndpoint.TOKEN, auth=(self.as_tuple()))

        # Get response from api
        response_json = response.json
        token = response_json["token"]

        if token is not None:
            return {"Authorization": f"Bearer {token}"}
        else:
            raise ddserr.JwtTokenGenerationError()


class DDSEndpoint:
    """Defines all DDS urls."""

    # Base url - local or remote
    BASE_ENDPOINT = "/api/v1"

    # User creation
    USER_ADD = BASE_ENDPOINT + "/user/add"
    USER_CONFIRM = "/confirm_invite/"
    USER_NEW = BASE_ENDPOINT + "/user/new"

    # Authentication - user and project
    TOKEN = BASE_ENDPOINT + "/user/token"
    ENCRYPTED_TOKEN = BASE_ENDPOINT + "/user/encrypted_token"

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

    # Display facility usage
    USAGE = BASE_ENDPOINT + "/usage"
    INVOICE = BASE_ENDPOINT + "/invoice"

    TIMEOUT = 5
