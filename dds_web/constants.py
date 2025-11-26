"""Shared constants used in the DDS API.

Using this will avoid e.g. circular imports and 
make it easier to maintain.

TODO: Move other constants here.
"""

# Timeout settings for upload and download
S3_READ_TIMEOUT = 300 # default is 60 seconds
S3_CONNECT_TIMEOUT = 60 # default is 60 seconds

# Import these constants when using '*'
__all__ = ["S3_READ_TIMEOUT", "S3_CONNECT_TIMEOUT"]
