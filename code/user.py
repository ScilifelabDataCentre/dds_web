#!/usr/bin/env python3
"""user.py"""


# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import

import base
from base import BaseHandler

import hashlib

import string

from code.dp_exceptions import DeliveryPortalException, SecurePasswordException, AuthenticationError

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


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

        # Get login form input
        try:
            # If username has been entered, get username and password
            # Otherwise, raise exception.
            if self.get_argument('username', None) is not None:
                username = self.get_body_argument('username')

                if not username.isalpha():
                    raise AuthenticationError(
                        "Username contains invalid characters.")
                else:
                    # If password has been entered, get password and generate secure password hash
                    # Otherwise, raise exception.
                    if self.get_argument('password', None) is not None:
                        try:
                            password = hashlib.sha256(
                                (self.get_body_argument('password')).encode('utf-8')).hexdigest()
                        except SecurePasswordException as se:
                            print(f"Password retrieval failed: {se}")
                    else:
                        raise DeliveryPortalException(
                            "No password was entered.")
            else:
                raise DeliveryPortalException("No user name was entered.")

        except DeliveryPortalException as de:
            print(f"Could not collect login information from DP: {de}")

        else:
            # Check if user exists and permissions
            auth, user_id = self.check_dp_access(username, password)

            # Sets current user if user exists
            if auth:
                try:
                    self.set_samesite_cookie(
                        cookie_name='user', cookie_value=user_id)
                except AuthenticationError as ae:
                    print(f"Samesite cookie could not be set: {ae}")
                else:
                    # Redirects to homepage via mainhandler
                    self.redirect(base.SITE_BASE_URL +
                                  self.reverse_url('home'))
            else:
                self.clear_cookie('user')
                self.write("Login incorrect.")


class LogoutHandler(BaseHandler):
    """Called by logout button.
    Logs user out, and redirects to login page via main handler."""

    def get(self):
        """Clears cookies and redirects to login page."""

        self.clear_cookie('user')
        self.redirect(base.SITE_BASE_URL + self.reverse_url('home'))


class ProfileHandler(BaseHandler):
    """Profile page."""

    def get(self):
        """Displays the profile page. """

        message = "This is the profile page where one can change password etc. "
        self.render('profile.html', curr_user=self.current_user,
                    message=message)
