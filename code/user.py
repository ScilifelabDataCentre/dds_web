#!/usr/bin/env python3
"""user.py"""


# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import

import base
from base import BaseHandler

import hashlib

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #

MAX_STREAMED_SIZE = 1024 * 1024 * 1024


# CLASSES ############################################################ CLASSES #

class LoginHandler(BaseHandler):
    """ Handles request to log in user. """

    def check_dp_access(self, username: str, password: str) -> (bool, str):
        """Check existance of user in database and the password validity."""

        dp_couch = self.couch_connect()
        user_db = dp_couch['user_db']
        for id_ in user_db:
            if username in [user_db[id_]['username'], user_db[id_]['contact_info']['email']]:
                if user_db[id_]['password_hash'] == password:
                    return True, id_

        return False, ""


    def post(self):
        """Called by login button.
        Gets inputs from form and checks user permissions."""

        # Get form input
        user_email = self.get_body_argument("user_email")
        # TODO: Change to secure password hashing
        password = hashlib.sha256(
            (self.get_body_argument("password")).encode('utf-8')).hexdigest()

        # Check if user exists
        auth, user_id = self.check_dp_access(user_email, password)

        # Sets current user if user exists
        if auth:
            self.set_samesite_cookie(cookie_name="user", cookie_value=user_id)
            # Redirects to homepage via mainhandler
            self.redirect(base.SITE_BASE_URL + self.reverse_url('home'))
        else:
            self.clear_cookie("user")
            self.write("Login incorrect.")


class LogoutHandler(BaseHandler):
    """Called by logout button.
    Logs user out, and redirects to login page via main handler."""

    def get(self):
        """Clears cookies and redirects to login page."""

        self.clear_cookie("user")
        self.redirect(base.SITE_BASE_URL + self.reverse_url('home'))


class ProfileHandler(BaseHandler):
    """Profile page."""

    def get(self):
        """Displays the profile page. """

        message = "This is the profile page where one can change password etc. "
        self.render('profile.html', curr_user=self.current_user,
                    message=message)
