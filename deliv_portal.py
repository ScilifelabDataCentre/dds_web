#!/usr/local/bin/python3


# IMPORTS ############################################################ IMPORTS #
import base64
import tornado.autoreload
import tornado.ioloop
import tornado.web
import uuid
import pymysql
import tornado_mysql

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
                     url(r"/project", ProjectHandler, name='project')
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
    """docstring for CreateDeliveryHandler"""
    def get(self):
        """"""
        self.render('create_delivery.html')

    #@tornado.web.authenticated
    def post(self):
        """"""
        self.render('create_delivery.html')


class LoginHandler(BaseHandler):
    """docstring for LoginHandler"""
    def check_permission(self, username, password):
        """"""
        # Establish database connection
        login_connection = pymysql.connect(host="localhost",
                                           user="root",
                                           password="Polarbear1",
                                           db="del_port_db")

        # Check if user exists
        try:
            with login_connection.cursor() as cursor:   # cursor used to interact with database
                sql = f"SELECT * FROM `users` WHERE `email`='{username}' AND `password`='{password}'"
                cursor.execute(sql)
                results = cursor.fetchall()
                if len(results) == 1:
                    return True
                else:
                    return False
        finally:
            login_connection.close()

    def get(self):
        """"""
        try:
            errormessage = self.get_argument("error")
        except:
            errormessage = ""

    def post(self):
        """"""
        # Get form input
        user_email = self.get_body_argument("user_email")
        password = self.get_body_argument("password")
        auth = self.check_permission(user_email, password)

        if auth:
            self.set_secure_cookie("user", user_email, expires_days=0.007)
            self.redirect(site_base_url + self.reverse_url('home'))
        else:
            self.clear_cookie("user")
            self.write("Login incorrect.")

class LogoutHandler(BaseHandler):
    """docstring for LogoutHandler"""
    def get(self):
        """"""
        self.clear_cookie("user")
        self.redirect(site_base_url + self.reverse_url('home'))


class MainHandler(BaseHandler):
    """docstring for MainHandler"""
    def get(self):
        """"""
        # self.current_user = False
        if not self.current_user:
            self.render('index.html')
        else:
            projects = self.get_user_projects()
            self.render('home.html', user=self.current_user)

    def get_user_projects(self):
        """"""
        getproj_connection = pymysql.connect(host="localhost",
                                     user="root", 
                                     password="Polarbear1",
                                     db="del_port_db")
        try:
            with getproj_connection.cursor() as cursor:   # cursor used to interact with database
                sql = f"SELECT * FROM `users` WHERE `email`='{username}' AND `password`='{password}'"
                cursor.execute(sql)
                results = cursor.fetchall()
                if len(results) == 1:
                    return True
                else:
                    return False
        finally:
            login_connection.close()



class ProjectHandler(BaseHandler):
    """"""
    def post(self):
        """"""
        self.redirect(site_base_url + self.reverse_url('home'))


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
        print("Database version: %s" % data)
    finally:
        # Disconnect from server
        connection.close()


# MAIN ################################################################## MAIN #
def main():
    """"""
    test_db_connection()

    # For devel puprose watch page changes
    tornado.autoreload.start()
    tornado.autoreload.watch("html_templates/index.html")
    tornado.autoreload.watch("html_templates/home.html")
    tornado.autoreload.watch("html_templates/create_delivery.html")

    application = ApplicationDP()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
