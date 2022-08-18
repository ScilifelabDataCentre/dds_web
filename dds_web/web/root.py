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
@cachetools.cached(
    cache=cachetools.TTLCache(maxsize=5, ttl=timedelta(seconds=10), timer=datetime.now),
    lock=threading.Lock(),
)
def open_troubleshooting():
    """Show troubleshooting document.

    Cache information:
    - Flask-Caching not used due to security vulnerability.
    - Args:
        - cache=cachetools.TTLCache: Time-to-live cache. timer() + ttl --> defines expiration time of cached item
        - lock: synchronize thread access to cache --> threadsafe
    """
    page_if_not_works = "https://scilifelab.atlassian.net/wiki/spaces/deliveryportal/pages/2192998453/2022+August+18+-+Troubleshooting"

    # Get troubleshooting doc from confluence
    try:
        response = requests.get(
            "https://scilifelab.atlassian.net/wiki/rest/api/content/2192998470?expand=space,metadata.labels,body.storage"
        )
        if not response.ok:
            err: str = "Failed getting troubleshooting information."
            flask.current_app.logger.warning(err)
            flask.abort(404, err)
        response_json = response.json()
    except (simplejson.JSONDecodeError, requests.exceptions.RequestException) as err:
        flask.current_app.logger.exception(f"Troubleshooting information could not be collected.\n{err}")
        return render_template("troubleshooting.html", confluence_link=page_if_not_works)

    # Get troubleshooting info
    info = response_json
    for key in ["body", "storage", "value"]:
        info = info.get(key)
        if not info:
            err = f"No '{key}' returned from troubleshooting page."
            flask.current_app.logger.warning(err)
            return render_template("troubleshooting.html", confluence_link=page_if_not_works)

    # Fix formatting
    # Code boxes
    pattern_found = re.findall(
        '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="(.*?)"><ac:plain-text-body><!\[CDATA\[',
        info,
    )
    for codeid in pattern_found:
        info = info.replace(
            f'<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="{codeid}"><ac:plain-text-body><![CDATA[',
            "<pre>",
        )

    # Info boxes
    info_box_start = re.findall(
        '<table data-layout="default" ac:local-id="(.*?)"><colgroup><col style="width: 760.0px;" /></colgroup><tbody><tr><td data-highlight-colour="(.*?)">',
        info,
    )
    for codeid in info_box_start:
        color = "lightgray"
        if codeid[1] == "#eae6ff":
            color = "purple"
        info = info.replace(
            f'<table data-layout="default" ac:local-id="{codeid[0]}"><colgroup><col style="width: 760.0px;" /></colgroup><tbody><tr><td data-highlight-colour="{codeid[1]}">',
            f'<div style="border: 3px solid {color}; padding: 10px; margin: 10px;"">',
        )

    # Additional fixes
    replacement_1 = {
        "<h2>": "<br><h2>",  # Add extra space
        "]]></ac:plain-text-body></ac:structured-macro>": "</pre>",  # end code box
        "</td></tr></tbody></table>": "</div>",  # end info box
    }
    for key, value in replacement_1.items():
        info = info.replace(key, value)

    return render_template("troubleshooting.html", info=info)


@pages.route("/status")
def get_status():
    """Return a simple status message to confirm that the system is ready."""
    return jsonify({"status": "ready"})


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template("404.html"), 404
