"Various utility functions and classes."

import datetime
import functools
import os

from contextlib import contextmanager
from flask import g, request, redirect, url_for, abort

# DECORATORS ####################################################### DECORATERS #

# Decorators for endpoints, taken from Per's Anubis package
def login_required(f):
    """Decorator for checking if logged in. Send to login page if not."""

    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not g.current_user:
            url = url_for("user.login", next=request.base_url)
            return redirect(url)
        return f(*args, **kwargs)

    return wrap


def admin_access_required(f):
    """Decorator for checking if the user have admin access else abort."""

    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not g.is_admin:
            return abort(403, "Only admin can access this page")
        return f(*args, **kwargs)

    return wrap


# context for changing working directory
@contextmanager
def working_directory(path, cleanup_after=False):
    """Contexter for changing working directory"""
    current_path = os.getcwd()
    try:
        if not os.path.exists(path):
            os.mkdir(path)
        os.chdir(path)
        yield
    finally:
        os.chdir(current_path)


def format_byte_size(size):
    """Take size in bytes and converts according to the size"""
    suffixes = ["bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    for suffix in suffixes:
        if size >= 1000:
            size /= 1000
        else:
            break
    return f"{size:.2} {suffix}"
