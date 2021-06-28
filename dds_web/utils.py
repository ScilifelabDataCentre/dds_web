"Various utility functions and classes."

import datetime
import functools
import os
import pathlib
import shutil
import json

import time
import pytz
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import pandas

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


def invoice_units():

    app.logger.debug("Executing scheduled job...")

    # Create invoice specification
    # TODO (ina): Change to Safespring API call
    parent_dir = pathlib.Path("").parent

    # From safespring
    old_file = parent_dir / pathlib.Path("development/invoicing/safespring_invoicespec.csv")

    current_time = timestamp(ts_format="%Y-%m-%d_%H-%M-%S")
    to_file = old_file
    # to_file = parent_dir / pathlib.Path(f"development/invoicing/{current_time}.csv")

    # shutil.copy(old_file, to_file)

    # Get data
    csv_contents = pandas.read_csv(to_file, sep=";", header=1)

    with app.app_context():
        try:
            all_facilities = models.Facility.query.all()
        except sqlalchemy.exc.SQLAlchemyError as err:
            app.logger.warning(
                f"Failed getting facility information from database. Cannot generate invoicing information: {err}"
            )
        else:
            for f in all_facilities:
                safespring_project_row = csv_contents.loc[csv_contents["project"] == f.safespring]
                # app.logger.debug(safespring_project_row.)

                # Total number of GB hours and cost saved in the db for the specific facility
                total_gbhours_db = 0.0

                usage = {}
                for p in f.projects:
                    usage[p.public_id] = {"gbhours": 0.0, "cost": 0.0}

                    for fl in p.files:
                        for v in fl.versions:
                            # Calculate hours of the current file
                            time_uploaded = datetime.datetime.strptime(
                                v.time_uploaded,
                                "%Y-%m-%d %H:%M:%S.%f%z",
                            )
                            time_deleted = datetime.datetime.strptime(
                                v.time_deleted if v.time_deleted else timestamp(),
                                "%Y-%m-%d %H:%M:%S.%f%z",
                            )
                            file_hours = (time_deleted - time_uploaded).seconds / (60 * 60)
                            # Calculate GBHours, if statement to avoid zerodivision exception
                            gb_hours = ((v.size_stored / 1e9) / file_hours) if file_hours else 0.0

                            # Save file version gbhours to project info and increase total facility sum
                            usage[p.public_id]["gbhours"] += gb_hours
                            total_gbhours_db += gb_hours

                for proj, vals in usage.items():
                    gbhour_perc = (
                        (vals["gbhours"] / total_gbhours_db)
                        if 0.0 not in [vals["gbhours"], total_gbhours_db]
                        else 0.0
                    )

                    usage[proj]["cost"] = safespring_project_row.subtotal.values[0] * gbhour_perc

                # Maybe uncomment later - saves calculated info to json file
                # new_file = parent_dir / pathlib.Path(
                #     f"development/invoicing/{f.id}_{current_time}.json"
                # )
                # with new_file.open(mode="w") as file:
                #     json.dump(usage, file)


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
    invoice_units,
    "cron",
    id="calc_costs",
    replace_existing=True,
    month="1-12",
    day="1-30",
    hour="0-23",
    minute="0-59",
    second="0,30",
)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())
