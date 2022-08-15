"""Global application routes.

Most of the app routes are in `dds_web/web/user.py`.
Here we have the routes that are not specific to a user.
"""
from flask import Blueprint, render_template, jsonify
from flask import current_app as app
from dds_web import forms
import re
import requests
from dds_web import cache
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
@cache.cached(timeout=50)
def open_troubleshooting():
    """Show troubleshooting document."""
    # Get troubleshooting doc from confluence
    try:
        response = requests.get("https://scilifelab.atlassian.net/wiki/rest/api/content/2192998470?expand=space,metadata.labels,body.storage")
        response_json = response.json()
    except (simplejson.JSONDecodeError, requests.exceptions.RequestException) as err:
        flask.current_app.logger.exception(err)
        flask.abort(404, "Troubleshooting information could not be collected.")

    # Get troubleshooting info
    info = response_json
    for key in ["body", "storage", "value"]:
        info=info.get(key)
        if not info:
            err = f"No '{key}' returned from troubleshooting page."
            flask.current_app.logger.warning(err)
            flask.abort(404, err)
    
    # Fix formatting
    # Code boxes
    pattern_found = re.findall('<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="(.*?)"><ac:plain-text-body><!\[CDATA\[', info)
    for codeid in pattern_found:
        info = info.replace(f'<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="{codeid}"><ac:plain-text-body><![CDATA[', "<pre>")    

    # Info boxes
    info_box_start = re.findall('<table data-layout="default" ac:local-id="(.*?)"><colgroup><col style="width: 760.0px;" /></colgroup><tbody><tr><td data-highlight-colour="#deebff">', info)
    for codeid in info_box_start:
        info = info.replace(f'<table data-layout="default" ac:local-id="{codeid}"><colgroup><col style="width: 760.0px;" /></colgroup><tbody><tr><td data-highlight-colour="#deebff">', '<div style="border: 3px solid lightgray; padding: 10px; margin: 10px;"">') 
    
    # Additional fixes
    replacement_1 = {
        "<h2>": "<br><h2>", 
        "]]></ac:plain-text-body></ac:structured-macro>": "</pre>",
        "</td></tr></tbody></table>": "</div>"
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
