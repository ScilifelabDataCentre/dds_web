"""" Default and base configuration handling """

import os

ROOT_DIRPATH = os.path.dirname(os.path.abspath(__file__))

# Default configurable values; modified by reading a JSON file in 'init'.
DEFAULT_SETTINGS = dict(
    ROOT_DIRPATH = ROOT_DIRPATH,
    SERVER_NAME = '127.0.0.1:5000',
    SITE_NAME = 'Data-Delivery-System',
    DEBUG = False,
    MIN_PASSWORD_LENGTH = 6,
    PERMANENT_SESSION_LIFETIME = 7 * 24 * 60 * 60, # seconds; 1 week
    DOC_DIRPATH = os.path.join(ROOT_DIRPATH, 'documentation'),
    TEMPLATES_AUTO_RELOAD = True
    )

def configit(app):
    """Configure the flask app with the default config values and
    site specifc config files in expected file location
    """
    app.config.from_mapping(DEFAULT_SETTINGS)
    try:
        # Look for site setting file from environment variable
        app.config.from_json(os.environ['DDS_SETTINGS_FILEPATH'])
    except:
        pass
