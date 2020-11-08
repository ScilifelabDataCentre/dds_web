"Various utility functions and classes."

# IMPORTS ########################################################### IMPORTS #


import functools

from flask import (g, request, redirect, url_for)


# FUNCTIONS ####################################################### FUNCTIONS #


# Decorators for endpoints, taken from Per's Anubis package
def login_required(f):
    "Decorator for checking if logged in. Send to login page if not."
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not g.current_user:
            url = url_for("user.login", next=request.base_url)
            return redirect(url)
        return f(*args, **kwargs)
    return wrap

