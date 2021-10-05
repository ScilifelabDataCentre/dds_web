"""Testing of the dds_web code with pytest."""

# Copied from dds_cli __init__.py:

__all__ = [
    "DDS_METHODS",
    "DDS_DIR_REQUIRED_METHODS",
    "DDS_PROJ_REQUIRED_METHODS",
    "DDS_PROJ_NOT_REQUIRED_METHODS",
    "DDSEndpoint",
]


###############################################################################
# VARIABLES ####################################################### VARIABLES #
###############################################################################

# Keep track of all allowed methods
DDS_METHODS = ["put", "get", "ls", "rm"]

# Methods to which a directory created by DDS
DDS_DIR_REQUIRED_METHODS = ["put", "get"]

# Methods which require a project ID
DDS_PROJ_REQUIRED_METHODS = ["put", "get"]

# Methods which do not require a project ID
DDS_PROJ_NOT_REQUIRED_METHODS = ["ls", "rm"]


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DDSEndpoint:
    """Defines all DDS urls."""

    # Base url - local or remote
    BASE_ENDPOINT = "/api/v1"

    # User creation
    USER_INVITE = BASE_ENDPOINT + "/user/invite"

    # Authentication - user and project
    TOKEN = BASE_ENDPOINT + "/user/token"

    # S3Connector keys
    S3KEYS = BASE_ENDPOINT + "/s3/proj"

    # File related urls
    FILE_NEW = BASE_ENDPOINT + "/file/new"
    FILE_MATCH = BASE_ENDPOINT + "/file/match"
    FILE_INFO = BASE_ENDPOINT + "/file/info"
    FILE_INFO_ALL = BASE_ENDPOINT + "/file/all/info"
    FILE_UPDATE = BASE_ENDPOINT + "/file/update"

    # Project specific urls
    PROJECT_SIZE = BASE_ENDPOINT + "/proj/size"

    # Listing urls
    LIST_PROJ = BASE_ENDPOINT + "/proj/list"
    LIST_FILES = BASE_ENDPOINT + "/files/list"

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
