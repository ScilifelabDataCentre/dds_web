"Various utility functions and classes."

import datetime
import functools
import os
import pathlib
import shutil

import time
import pytz
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

from contextlib import contextmanager
from flask import g, request, redirect, url_for, abort, current_app
from dds_web.database import models
import sqlalchemy
from dds_web import app, db, timestamp

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


def format_byte_size(b):
    """Take size in bytes and converts according to the size"""
    b = int(b)

    if b == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    for p in reversed(range(5)):
        if b > pow(1000, p):
            return "{} {}".format(round(b / pow(1000, p), 2), units[p])


def print_date_time():
    print(
        datetime.datetime.now(tz=pytz.timezone("Europe/Stockholm")),
        flush=True,
    )

    # Create invoice specification
    # TODO (ina): Change to Safespring API call
    parent_dir = pathlib.Path("").parent
    current_time = timestamp()
    app.logger.debug("current time: %s", current_time)
    old_file = parent_dir / pathlib.Path("development/invoicing/safespring_invoicespec.csv")
    to_file = parent_dir / pathlib.Path("development/invoicing/test1.csv")
    shutil.copy(old_file, to_file)  # For newer Python.

    with app.app_context():
        try:
            all_facilities = models.Facility.query.all()
        except sqlalchemy.exc.SQLAlchemyError as err:
            app.logger.warning(
                f"Failed getting facility information from database. Cannot generate invoicing information: {err}"
            )
        else:
            for f in all_facilities:
                pass
            app.logger.debug(all_facilities)


scheduler = BackgroundScheduler(
    {
        "apscheduler.jobstores.default": {
            "type": "sqlalchemy",
            "url": app.config.get("SQLALCHEMY_DATABASE_URI"),
        },
        "apscheduler.timezone": "Europe/Stockholm",
    }
)

scheduler.add_job(
    print_date_time,
    "cron",
    month="1-12",
    day="1-30",
    hour="0-23",
    minute="0-59",
    second="1,30",
)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())
