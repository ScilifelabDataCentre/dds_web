#!/usr/bin/env python3
"""base.py description"""

# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import
from http.cookies import Morsel
import tornado.web
import couchdb

from utils.config import parse_config


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #

CONFIG = parse_config()
SITE_BASE_URL = f'{CONFIG["site_base_url"]}:{CONFIG["site_port"]}'

Morsel._reserved['samesite'] = 'SameSite'

# CLASSES ############################################################ CLASSES #

class BaseHandler(tornado.web.RequestHandler):
    """Main class used for general functions applying to entire application. """

    def set_samesite_cookie(self, cookie_name, cookie_value):
        """Sets a samesite cookie"""

        self.set_secure_cookie(cookie_name, cookie_value, expires_days=0.1, samesite="lax")

    def get_current_user(self):
        """Gets the current user - used for login check etc. """

        return self.get_secure_cookie("user")

    @classmethod
    def couch_connect(cls):
        """Connect to a couchdb interface."""
        couch = couchdb.Server(f'{CONFIG["couch_url"]}:{CONFIG["couch_port"]}')
        couch.login(CONFIG['couch_username'], CONFIG['couch_password'])
        return couch
