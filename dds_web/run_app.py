"Web API for Data Delivery System"

# Gevent monkey-patch must run before any other imports that use sockets, threading, or blocking I/O
# (required for Gunicorn with --worker-class=gevent)
import gevent.monkey

gevent.monkey.patch_all()

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library

# Installed

# Own modules
from dds_web import create_app


####################################################################################################
# Global variable for Gunicorn ###################################### Global variable for Gunicorn #
####################################################################################################

app_obj = create_app()
