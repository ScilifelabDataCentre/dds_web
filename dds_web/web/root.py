"""Global application routes.

Most of the app routes are in `dds_web/web/user.py`.
Here we have the routes that are not specific to a user.
"""
from flask import Blueprint, render_template, jsonify
from flask import current_app as app
from dds_web import forms


pages = Blueprint("pages", __name__)


@pages.route("/", methods=["GET"])
def home():
    """Home page."""
    form = forms.LoginForm()
    return render_template("home.html", form=form)


@pages.route("/status")
def get_status():
    """Return a simple status message to confirm that the system is ready."""
    return jsonify({"status": "ready"})


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template("404.html"), 404
