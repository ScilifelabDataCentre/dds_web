#!/usr/bin/env python3
"""user.py"""


# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import
import base
from base import BaseHandler
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
import hashlib
import string
import re
from dp_exceptions import DeliveryPortalException, SecurePasswordException, \
    AuthenticationError, CouchDBException

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #

class LoginHandler(BaseHandler):
    """ Handles request to log in user. """

    def check_dp_access(self, username: str, password: str) -> (bool, str):
        """Check existance of user in database and the password validity."""

        user_db = self.couch_connect()['user_db']

        if user_db != {}:
            for id_ in user_db:
                if username == user_db[id_]['username']:
                    correct_password = user_db[id_]['password']['hash']
                    settings = user_db[id_]['password']['settings']

                    split_settings = settings.split('$')
                    for i in [1, 2, 3, 4]:
                        split_settings[i] = int(split_settings[i])

                    kdf = Scrypt(salt=bytes.fromhex(split_settings[0]),
                                 length=split_settings[1],
                                 n=2**split_settings[2],
                                 r=split_settings[3],
                                 p=split_settings[4],
                                 backend=default_backend())
                    input_password = kdf.derive(password.encode('utf-8')).hex()
                    if correct_password == input_password:
                        try:
                            self.set_secure_cookie('user',
                                                   id_, expires_days=0.1)

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
                            access_granted = self.check_dp_access(username=username,
                                                             password=self.get_body_argument('password'))
                             # Sets current user if user exists
                            if access_granted:
                                self.redirect(base.SITE_BASE_URL + self.reverse_url('home'))
                            else:
                                self.clear_cookie('user')
                                self.write("Login incorrect.")
                        except SecurePasswordException as se:
                            print(f"Password retrieval failed: {se}")
                    else:
                        raise DeliveryPortalException(
                            "No password was entered.")
            else:
                raise DeliveryPortalException("No user name was entered.")

        except DeliveryPortalException as de:
            print(f"Could not collect login information from DP: {de}")

           


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
