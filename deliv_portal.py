#!/usr/local/bin/python3

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

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")


class MainHandler(BaseHandler):
    def get(self):
        # self.current_user = False
        if not self.current_user:
            self.render('home_base.php')
        else:
            self.render('home_login.html', user=self.current_user)



class LoginHandler(BaseHandler):
    def post(self):
        # Get form input
        user_email = self.get_body_argument("user_email")
        password = self.get_body_argument("password")

        # Establish database connection
        login_connection = pymysql.connect(host="localhost",
                                           user="root",
                                           password="Polarbear1",
                                           db="del_port_db")

        # Check if user exists
        try:
            with login_connection.cursor() as cursor:   # cursor used to interact with database
                sql = f"SELECT * FROM `users` WHERE `email`='{user_email}' AND `password`='{password}'"
                cursor.execute(sql)
                results = cursor.fetchall()
                if len(results) == 1:
                    self.set_secure_cookie("user", user_email, expires_days=0.007)
                    self.redirect(site_base_url + self.reverse_url('home'))
        finally:
            login_connection.close()


class CreateDeliveryHandler(BaseHandler):
    def get(self):
        self.render('create_delivery.html')

    #@tornado.web.authenticated
    def post(self):
        self.render('create_delivery.html')


def main():
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



    url = tornado.web.url
    handlers = [ url(r"/", MainHandler, name='home'),
                 url(r"/login", LoginHandler, name='login'),
                 url(r"/create", CreateDeliveryHandler, name='create')
                 ]

    # For devel puprose watch page changes
    tornado.autoreload.start()
    tornado.autoreload.watch("html_templates/home_base.php")
    tornado.autoreload.watch("html_templates/home_login.html")
    tornado.autoreload.watch("html_templates/create_delivery.html")
    tornado.autoreload.watch("html_templates/login_user.php")

    application = tornado.web.Application(handlers = handlers,
                                          xsrf_cookies = True,
                                          #cookie_secret = base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
                                          cookie_secret = config["cookie_secret"], #for dev purpose, shoulde be removed in the end
                                          template_path = "html_templates",
                                          static_path = "files")
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
