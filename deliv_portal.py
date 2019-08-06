#!/usr/bin/env python

import base64
import tornado.autoreload
import tornado.ioloop
import tornado.web
import uuid

from utils.config import parse_config

config = parse_config()
site_base_url = config["site_base_url"]

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")


class MainHandler(BaseHandler):
    def get(self):
        if not self.current_user:
            self.render('home_base.html')
        else:
            self.render('home_login.html', user=self.current_user)


class LoginHandler(BaseHandler):
    def post(self):
        user_email = self.get_body_argument("user_email")
        password = self.get_body_argument("password")
        self.set_secure_cookie("user", user_email, expires_days=2)
        self.redirect(site_base_url + self.reverse_url('home'))


class CreateDeliveryHandler(BaseHandler):
    def get(self):
        self.render('create_delivery.html')

    #@tornado.web.authenticated
    def post(self):
        self.render('create_delivery.html')


def main():
    
    url = tornado.web.url
    handlers = [ url(r"/", MainHandler, name='home'),
                 url(r"/login", LoginHandler, name='login'),
                 url(r"/create", CreateDeliveryHandler, name='create')
               ]
    
    # For devel puprose watch page changes
    tornado.autoreload.start()
    tornado.autoreload.watch("html_templates/home_base.html")
    tornado.autoreload.watch("html_templates/home_login.html")
    tornado.autoreload.watch("html_templates/create_delivery.html")
    
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
