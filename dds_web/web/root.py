"""Global application routes.

Most of the app routes are in `dds_web/web/user.py`.
Here we have the routes that are not specific to a user.
"""
from datetime import datetime, timedelta
import functools
import threading
from flask import Blueprint, render_template, jsonify
from flask import current_app as app
from dds_web import forms
import re
import requests
import cachetools
import simplejson
import flask
import sqlalchemy


pages = Blueprint("pages", __name__)


@pages.route("/", methods=["GET"])
def home():
    """Home page."""
    form = forms.LoginForm()
    return render_template("home.html", form=form)


@pages.route("/policy", methods=["GET"])
def open_policy():
    """Show privacy policy."""
    return render_template("policy.html")


@pages.route("/trouble", methods=["GET"])
def open_troubleshooting():
    """Show troubleshooting document."""

    return render_template("troubleshooting.html")


@pages.route("/technical", methods=["GET"])
def open_technical_overview():
    """Show technical overview document."""
    return render_template("technical_overview.html")


@pages.route("/status")
def get_status():
    """Return a simple status message to confirm that the system is ready."""
    return jsonify({"status": "ready"})


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template("errorpages/404.html"), 404


@app.errorhandler(sqlalchemy.exc.SQLAlchemyError)
def handle_sqlalchemyerror(e):
    flask.current_app.logger.exception(e)
    return render_template("errorpages/sqlalchemy.html"), 500


@app.errorhandler(503)
def maintenance_ongoing(e):
    return flask.render_template("errorpages/503.html"), 503
