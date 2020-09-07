"Configuration."

# IMPORTS ########################################################### IMPORTS #

# Standard Library
import os

# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #

ROOT_DIRPATH = os.path.dirname(os.path.abspath(__file__))

# Default configurable values; modified by reading a JSON file in 'init'.
DEFAULT_SETTINGS = dict(
    ROOT_DIRPATH=ROOT_DIRPATH,
    WTF_CSRF_ENABLED=True,
    WTF_CSRF_TIME_LIMIT=3600,
    SERVER_NAME='127.0.0.1:5000',
    SERVER_HOST='0.0.0.0',
    SERVER_PORT=5000,
    SITE_NAME='Data Delivery System',
    DEBUG=False,
    MIN_PASSWORD_LENGTH=6,
    PERMANENT_SESSION_LIFETIME=7 * 24 * 60 * 60,  # seconds; 1 week
    DOC_DIRPATH=os.path.join(ROOT_DIRPATH, 'documentation'),
    TEMPLATES_AUTO_RELOAD=True
)

# FUNCTIONS ####################################################### FUNCTIONS #


def init(app):
    """Perform the configuration of the Flask app.
    Set the defaults, and then read JSON settings file.
    Check the environment for a specific set of variables and use if defined.
    """
    # Set the defaults specified above.
    app.config.from_mapping(DEFAULT_SETTINGS)
    # Modify the configuration from a JSON settings file.
    try:
        filepath = os.environ["DDS_SETTINGS_FILEPATH"]
    except Exception as e:
        print(f"ERROR: {e}")
    else:
        app.config.from_json(filepath)

    # assert app.config["SECRET_KEY"]
