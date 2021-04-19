"Various utility functions and classes."

import datetime
import functools

from flask import (g, request, redirect, url_for)

# DECORATORS ####################################################### DECORATERS #

# Decorators for endpoints, taken from Per's Anubis package
def login_required(f):
    """ Decorator for checking if logged in. Send to login page if not."""
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not g.current_user:
            url = url_for("user.login", next=request.base_url)
            return redirect(url)
        return f(*args, **kwargs)
    return wrap

def get_timestamp(tformat="%y%m%d%H%M%S%f"):
    """ funtcion to return string of current time in requested format """
    return datetime.datetime.now().strftime(tformat)
