#!/usr/bin/env python3
"""info.py"""


# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import
from base import BaseHandler

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #

MAX_STREAMED_SIZE = 1024 * 1024 * 1024


# CLASSES ############################################################ CLASSES #

class ContactHandler(BaseHandler):
    """Contact page."""

    def get(self):
        """get"""
        message = "This is the page where contact info is displayed. "
        self.render("contact_page.html", user=self.current_user, message=message)


class InfoHandler(BaseHandler):
    """Information page."""

    def get(self):
        """get"""
        message = "This is an information page about the dp."
        self.render("info_dp.html", curr_user=self.current_user, message=message)
