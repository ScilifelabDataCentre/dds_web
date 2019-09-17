#!/usr/bin/env python3
"""user.py"""


# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import

import base
from base import BaseHandler

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #

MAX_STREAMED_SIZE = 1024 * 1024 * 1024


# CLASSES ############################################################ CLASSES #

class LoginHandler(BaseHandler):
    """ Handles request to log in user. """

    def check_permission(self, username, password):
        """Called by post.
        Connects to database and checks if user exists."""

        couch = self.couch_connect()
        database = couch['dp_users']

        # Searches database for user with matching email and password
        for user_id in database:
            if (database[user_id]['user']['email'] == username and
                    database[user_id]['user']['password'] == password):
                return True, user_id

        return False, ""    # Returns false and "" if user not found

    def post(self):
        """Called by login button.
        Gets inputs from form and checks user permissions."""

        # Get form input
        user_email = self.get_body_argument("user_email")
        password = self.get_body_argument("password")

        # Check if user exists
        auth, user_id = self.check_permission(user_email, password)

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
        self.render('profile.html', curr_user=self.current_user, message=message)
