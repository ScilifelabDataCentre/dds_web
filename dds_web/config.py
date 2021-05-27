class Config(object):
    """Base config"""

    SITE_NAME = "Data Delivery System"
    SECRET_KEY = "RANDOM_HASH_HERE"

    # DB related config
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://TEST_USER:TEST_PASSWORD@db/DeliverySystem"
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Data related config
    MAX_CONTENT_LENGTH = 16777216
    MAX_DOWNLOAD_LIMIT = 1000000000

    # Expected paths - these are the bind paths *inside* the container
    USE_LOCAL_DB = True
    LOGS_DIR = "/dds_web/logs"
    UPLOAD_FOLDER = "/dds_web/uploads"
    DOWNLOAD_FOLDER = "/dds_web/downloads"
    LOCAL_TEMP_CACHE = "/dds_web/local_temp_cache"
    DDS_S3_CONFIG = "/code/dds_web/s3_config_example.json"
    DDS_SAFE_SPRING_PROJECT = "YOUR-PROJECT-ID"

    # Devel settings
    TEMPLATES_AUTO_RELOAD = True
