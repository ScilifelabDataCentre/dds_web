#!/usr/bin/env python3
"""Delivery portal application."""


# IMPORTS ############################################################ IMPORTS #
from __future__ import absolute_import
import logging
import tornado.autoreload
import tornado.ioloop
import tornado.gen
import tornado.web

import base
from base import BaseHandler
from info import InfoHandler, ContactHandler
from user import LoginHandler, LogoutHandler, ProfileHandler
from project import ProjectHandler, ProjectStatus
from file import UploadHandler


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #

class ApplicationDP(tornado.web.Application):
    """docstring for ApplicationDP."""

    def __init__(self):
        """ Initializes the application incl. handlers. """
        url = tornado.web.url
        handlers = [url(r"/", MainHandler, name='home'),
                    url(r"/login", LoginHandler, name='login'),
                    url(r"/logout", LogoutHandler, name='logout'),
                    url(r"/project/(?P<projid>.*)", ProjectHandler, name='project'),
                    url(r"/status/(?P<projid>.*)", ProjectStatus, name='status'),
                    url(r"/profile", ProfileHandler, name='profile'),
                    url(r"/info", InfoHandler, name='info'),
                    url(r"/contact", ContactHandler, name="contact"),
                    url(r"/upload/(?P<projid>.*)", UploadHandler, name="upload")
                    ]
        settings = {
            # "xsrf_cookies":True,
            # "cookie_secret":base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
            "cookie_secret":base.CONFIG["cookie_secret"], #for dev purpose
            # "cookie_secret": "0123456789ABCDEF",
            "template_path":"html_templates",
            "static_path":"files",
            }

        if base.CONFIG.get('development_mode'):
            settings['debug'] = True
            settings['develop'] = True
            logging.getLogger().setLevel(logging.DEBUG)

        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(BaseHandler):
    """Checks if user is logged in and redirects to home page."""

    def get(self):
        """Renders login page if not logged in, otherwise homepage."""

        if not self.current_user:
            self.render('index.html')
        else:
            # Get projects associated with user and send to home page
            # with user and project info
            projects, email, is_facility = self.get_user_projects()

            homepage = ""
            if is_facility:
                homepage = "facility_home.html"
            else:
                homepage = "home.html"

            self.render(homepage, curr_user=self.current_user, email=email,
                        projects=projects)

    def get_user_projects(self):
        """Connects to database and saves projects in dictionary."""

        curr_user = tornado.escape.xhtml_escape(self.current_user)   # Current user

        couch = self.couch_connect()
        user_db = couch['dp_users']
        proj_db = couch['projects']

        projects = {}

        # Gets all projects for current user and save projects
        # and their associated information
        if 'projects' in user_db[curr_user]:
            for proj in user_db[curr_user]['projects']:
                projects[proj] = proj_db[proj]['project_info']

        return projects, user_db[curr_user]['user']['email'], \
            ("facility" in user_db[curr_user]["user"])


# FUNCTIONS ######################################################## FUNCTIONS #

# MAIN ################################################################## MAIN #
def main():
    """main"""

    # For devel puprose watch page changes
    if base.CONFIG.get('development_mode'):
        tornado.autoreload.start()
        tornado.autoreload.watch("html_templates/index.html")
        tornado.autoreload.watch("html_templates/home.html")
        tornado.autoreload.watch("html_templates/project_page.html")
        tornado.autoreload.watch("html_templates/style.css")
        tornado.autoreload.watch("html_templates/profile.html")
        tornado.autoreload.watch("html_templates/info_dp.html")
        tornado.autoreload.watch("html_templates/contact_page.html")

    application = ApplicationDP()
    application.listen(base.CONFIG["site_port"])
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
