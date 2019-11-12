#!/usr/bin/env python3
"""user.py"""


# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import
import base
from base import BaseHandler
import hashlib
import string
import re
from dp_exceptions import DeliveryPortalException, SecurePasswordException, AuthenticationError, CouchDBException

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #

class LoginHandler(BaseHandler):
    """ Handles request to log in user. """

    def check_dp_access(self, username: str, password: str) -> (bool, str):
        """Check existance of user in database and the password validity."""

        user_db = self.couch_connect()['user_db']   # Connect and get user database
        
        if user_db != {}:       
            for id_ in user_db:
                if username == user_db[id_]['username']:
                    if user_db[id_]['password_hash'] == password:
                        try: 
                            self.set_secure_cookie('user', id_, expires_days=0.1)
                        except AuthenticationError as ae: 
                            print(f"Cookie could not be set: {ae}")
                        else: 
                            return True
        else:
            raise CouchDBException("The database 'user_db' is empty!")

        return False

    def post(self):
        """Called by login button.
        Gets inputs from form and checks user permissions."""

        username = ""
        password = ""

        # Get login form input
        try:
            # If username has been entered, get username and password
            # Otherwise, raise exception.
            if self.get_argument('username', None) is not None:
                username = self.get_body_argument('username')

                if not re.match("^[A-Za-z0-9]+$", username):
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
            auth = self.check_dp_access(username, password)

            # Sets current user if user exists
            if auth:
                self.redirect(base.SITE_BASE_URL + self.reverse_url('home'))
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
