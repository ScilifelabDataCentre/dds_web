#!/usr/bin/env python3


# IMPORTS ############################################################ IMPORTS #
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

from utils.config import parse_config
config = parse_config()
site_base_url = config["site_base_url"]

from tornado.options import define, options
define("port", default=8888, help="run on the given port", type=int)


# CLASSES ############################################################ CLASSES #
class ApplicationDP(tornado.web.Application):
    """docstring for ApplicationDP."""

    def __init__(self):
        """"""
        url = tornado.web.url
        handlers = [ url(r"/", MainHandler, name='home'),
                     url(r"/login", LoginHandler, name='login'),
                     url(r"/create", CreateDeliveryHandler, name='create'),
                     url(r"/logout", LogoutHandler, name='logout'),
                     url(r"/project/(?P<projid>.*)", ProjectHandler, name='project'),
                     # url(r"/files/(?P<pid>.*)", FileHandler, name='files')
                     ]
        settings = {"xsrf_cookies":True,
                    #"cookie_secret":base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
                    "cookie_secret":config["cookie_secret"], #for dev purpose, shoulde be removed in the end
                    "template_path":"html_templates",
                    "static_path":"files"
                    }
        tornado.web.Application.__init__(self, handlers, **settings)


class BaseHandler(tornado.web.RequestHandler):
    """docstring for BaseHandler"""
    def get_current_user(self):
        """"""
        return self.get_secure_cookie("user")


class CreateDeliveryHandler(BaseHandler):
    """Called by create button on home page.
    Renders form for a new delivery. """

    def get(self):
        """Renders form for a new delivery."""
        self.render('create_delivery.html')

    #@tornado.web.authenticated
    # def post(self):
    #     """"""
    #     self.render('create_delivery.html')


class FileHandler(BaseHandler):
    """docstring for FileHandler"""
    def get(self, pid):
        """"""
        self.render('view_all.html')


class LoginHandler(BaseHandler):
    """ Handles request to log in user. """

    def check_permission(self, username, password):
        """Called by post.
        Connects to database and checks if user exists."""

        couch = couchdb.Server("http://admin:admin@localhost:5984/")
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
            projects = self.get_user_projects()
            self.render('home.html', user=self.current_user,
                        projects=projects)

    def get_user_projects(self):
        """Connects to database and saves projects in dictionary."""
        user = tornado.escape.xhtml_escape(self.current_user)   # Current user

        couch = couchdb.Server("http://admin:admin@localhost:5984/")
        user_db = couch['dp_users']
        proj_db = couch['projects']

        projects = {}

        # Gets all projects for current user and save projects
        # and their associated information
        for proj in user_db[user]['projects']:
            projects[proj] = proj_db[proj]['project_info']

        return projects


class ProjectHandler(BaseHandler):
    """Called by "See project" button.
    Connects to database and collects all files
    associated with the project and user. Renders project page."""

    def get(self, projid):
        """"""
        couch = couchdb.Server("http://admin:admin@localhost:5984/")
        proj_db = couch['projects']

        project_info = proj_db[projid]['project_info']

        files = {}
        if 'files' in proj_db[projid]:
            files = proj_db[projid]['files']

        self.render('project_page.html', user=self.current_user,
                    files=files, project=project_info)


# FUNCTIONS ######################################################## FUNCTIONS #
def test_db_connection():
    """Tests connection to database"""
    try:
        # Open database connection
        connection = pymysql.connect(host="localhost",
                                     user="root",
                                     password="Polarbear1",
                                     db="del_port_db")

        # prepare a cursor object
        cursor = connection.cursor()

        # Execute sql query: What is the database version?
        cursor.execute("SELECT VERSION()")

        # Fetch a single row
        data = cursor.fetchone()
        print(f"Database version: {data}")
    finally:
        # Disconnect from server
        connection.close()


# MAIN ################################################################## MAIN #
def main():
    """"""
    # test_db_connection()

    # For devel puprose watch page changes
    tornado.autoreload.start()
    tornado.autoreload.watch("html_templates/index.html")
    tornado.autoreload.watch("html_templates/home.html")
    tornado.autoreload.watch("html_templates/create_delivery.html")
    tornado.autoreload.watch("html_templates/project_page.html")
    tornado.autoreload.watch("html_templates/style.css")

    application = ApplicationDP()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
