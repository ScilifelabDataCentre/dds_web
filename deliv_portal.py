#!/usr/bin/env python3


# IMPORTS ############################################################ IMPORTS #
import logging

import base64
import tornado.autoreload
import tornado.ioloop
import tornado.gen
import tornado.web
import uuid
import pymysql
import tornado_mysql
import couchdb
import re
import time
import sys

from datetime import date

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from utils.config import parse_config
config = parse_config()
site_base_url = f'{config["site_base_url"]}:{config["site_port"]}'

from tornado.options import define, options
define("port", default=config['site_port'], help="run on the given port", type=int)


# CLASSES ############################################################ CLASSES #

MAX_STREAMED_SIZE = 1024 * 1024 * 1024

class ApplicationDP(tornado.web.Application):
    """docstring for ApplicationDP."""

    def __init__(self):
        """ Initializes the application incl. handlers. """
        url = tornado.web.url
        handlers = [ url(r"/", MainHandler, name='home'),
                     url(r"/login", LoginHandler, name='login'),
                     url(r"/create", CreateDeliveryHandler, name='create'),
                     url(r"/logout", LogoutHandler, name='logout'),
                     url(r"/project/(?P<projid>.*)", ProjectHandler, name='project'),
                     url(r"/profile", ProfileHandler, name='profile'),
                     url(r"/info", InfoHandler, name='info'),
                     url(r"/contact", ContactHandler, name="contact"),
                     url(r"/upload/(?P<projid>.*)", UploadHandler, name="upload")
                     ]
        settings = {"xsrf_cookies":True,
                    #"cookie_secret":base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
                    "cookie_secret":config["cookie_secret"], #for dev purpose, shoulde be removed in the end
                    # "cookie_secret": "0123456789ABCDEF",
                    "template_path":"html_templates",
                    "static_path":"files"
                    }

        if config.get('development_mode'):
            settings['debug'] = True
            settings['develop'] = True
            logging.getLogger().setLevel(logging.DEBUG)

        tornado.web.Application.__init__(self, handlers, **settings)


class BaseHandler(tornado.web.RequestHandler):
    """Main class used for general functions applying to entire application. """

    def get_current_user(self):
        """Gets the current user - used for log in check etc. """

        return self.get_secure_cookie("user")

    def couch_connect(self):
        """Connect to a couchdb interface."""
        couch = couchdb.Server(f'{config["couch_url"]}:{config["couch_port"]}')
        couch.login(config['couch_username'], config['couch_password'])
        return couch


class ContactHandler(BaseHandler):
    """Contact page."""

    def get(self):
        message = "This is the page where contact info is displayed. "
        self.render("contact_page.html", user=self.current_user, message=message)


class CreateDeliveryHandler(BaseHandler):
    """Called by create button on home page.
    Renders form for a new delivery. """

    def get(self):
        """Renders form for a new delivery."""
        self.render('create_delivery.html', user=self.current_user,
                    pid="dgu8y3488hdfs8dh88r3")

    #@tornado.web.authenticated
    # def post(self):
    #     """"""
    #     self.render('create_delivery.html')


class InfoHandler(BaseHandler):
    """Information page."""

    def get(self):
        message = "This is an information page about the dp."
        self.render("info_dp.html", user=self.current_user, message=message)


class LoginHandler(BaseHandler):
    """ Handles request to log in user. """

    def check_permission(self, username, password):
        """Called by post.
        Connects to database and checks if user exists."""

        couch = self.couch_connect()
        db = couch['dp_users']

        # Searches database for user with matching email and password
        for id in db:
            for part in db[id]['user']:
                if db[id]['user']['email'] == username and db[id]['user']['password'] == password:
                    return True, id

        return False, ""    # Returns false and "" if user not found

    def get(self):
        """"""
        try:
            errormessage = self.get_argument("error")
        except:
            errormessage = ""

    def post(self):
        """Called by login button.
        Gets inputs from form and checks user permissions."""

        # Get form input
        user_email = self.get_body_argument("user_email")
        password = self.get_body_argument("password")

        # Check if user exists
        auth, id = self.check_permission(user_email, password)

        # Sets current user if user exists
        if auth:
            self.set_secure_cookie("user", id, expires_days=0.1)
            # Redirects to homepage via mainhandler
            self.redirect(site_base_url + self.reverse_url('home'))
        else:
            self.clear_cookie("user")
            self.write("Login incorrect.")


class LogoutHandler(BaseHandler):
    """Called by logout button.
    Logs user out, and redirects to login page via main handler."""

    def get(self):
        """Clears cookies and redirects to login page."""

        self.clear_cookie("user")
        self.redirect(site_base_url + self.reverse_url('home'))


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

            homepage=""
            if is_facility:
                homepage = "facility_home.html"
            else:
                homepage = "home.html"

            self.render(homepage, user=self.current_user, email=email,
                        projects=projects)

    def get_user_projects(self):
        """Connects to database and saves projects in dictionary."""

        user = tornado.escape.xhtml_escape(self.current_user)   # Current user

        couch = self.couch_connect()
        user_db = couch['dp_users']
        proj_db = couch['projects']

        projects = {}

        # Gets all projects for current user and save projects
        # and their associated information
        if 'projects' in user_db[user]:
            for proj in user_db[user]['projects']:
                projects[proj] = proj_db[proj]['project_info']

        return projects, user_db[user]['user']['email'], ("facility" in user_db[user]["user"])


class ProfileHandler(BaseHandler):
    """Profile page."""

    def get(self):
        """Displays the profile page. """

        message="This is the profile page where one can change password etc. "
        self.render('profile.html', user=self.current_user, message=message)


class ProjectHandler(BaseHandler):
    """Called by "See project" button.
    Connects to database and collects all files
    associated with the project and user. Renders project page."""

    def post(self, projid):
        """"""

        couch = self.couch_connect()

        proj_name = self.get_body_argument('prj_name')
        proj_category = self.get_body_argument('prj_ord_cat')
        proj_id = self.get_body_argument('prj_ord_id')
        proj_description = self.get_body_argument('prj_desc')

        pi_name = self.get_body_argument('prj_pi_name')
        pi_email = self.get_body_argument('prj_pi_email')

    def get(self, projid):
        """Renders the project page with projects and associated files."""

        # Current project
        self.set_secure_cookie("project", projid, expires_days=0.1)

        # Connect to db
        couch = self.couch_connect()
        proj_db = couch['projects']

        project_info = proj_db[projid]['project_info']

        # Save project files in dict 
        files = {}
        if 'files' in proj_db[projid]:
            files = proj_db[projid]['files']

        self.render('project_page.html', user=self.current_user,
                    files=files, projid=projid, project=project_info,
                    addfiles=(self.get_argument('uploadfiles', None) is not None))


class UploadHandler(BaseHandler):
    """Class. Handles the upload of the file."""

    def post(self, projid):

        # Checks if there are files "uploaded"
        files = []
        try:
            files = self.request.files['filesToUpload']
        except:
            pass

        # Connects to the database
        couch = self.couch_connect()            # couchdb
        proj_db = couch['projects']             # database: projects
        curr_proj = proj_db[projid]             # current project
        curr_proj_files = curr_proj['files']    # files assoc. with project

        # Save files (now uploaded)
        for f in files:
            filename = f['filename']

            try:
                with open(filename, "wb") as out:
                    out.write(f['body'])
            finally:
                curr_proj_files[filename] = {
                    "size": sys.getsizeof(filename),
                    "format": filename.split(".")[-1],
                    "date_uploaded": date.today().strftime("%Y-%m-%d"),
                }

        # Save couchdb --> updated
        # and show the project page again.
        try:
            proj_db.save(curr_proj)
        finally:
            self.render('project_page.html', user=self.current_user,
                        projid=projid, project=curr_proj['project_info'], files=curr_proj_files,
                        addfiles=(self.get_argument('uploadfiles', None) is not None))


# FUNCTIONS ######################################################## FUNCTIONS #

# MAIN ################################################################## MAIN #
def main():
    """"""

    # For devel puprose watch page changes
    if config.get('development_mode'):
        tornado.autoreload.start()
        tornado.autoreload.watch("html_templates/index.html")
        tornado.autoreload.watch("html_templates/home.html")
        tornado.autoreload.watch("html_templates/project_page.html")
        tornado.autoreload.watch("html_templates/style.css")
        tornado.autoreload.watch("html_templates/profile.html")
        tornado.autoreload.watch("html_templates/info_dp.html")
        tornado.autoreload.watch("html_templates/contact_page.html")

    application = ApplicationDP()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
