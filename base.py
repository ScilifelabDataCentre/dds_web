#!/usr/bin/env python3
"""base.py description"""

# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import
import tornado.web
import couchdb

from utils.config import parse_config


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #

CONFIG = parse_config()
SITE_BASE_URL = f'{CONFIG["site_base_url"]}:{CONFIG["site_port"]}'


# CLASSES ############################################################ CLASSES #

class BaseHandler(tornado.web.RequestHandler):
    """Main class used for general functions applying to entire application. """

    def get_current_user(self):
        """Gets the current user - used for login check etc. """

        return self.get_secure_cookie("user")

    @classmethod
    def couch_connect(cls):
        """Connect to a couchdb interface."""
        couch = couchdb.Server(f'{CONFIG["couch_url"]}:{CONFIG["couch_port"]}')
        couch.login(CONFIG['couch_username'], CONFIG['couch_password'])
        return couch
