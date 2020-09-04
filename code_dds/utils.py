"Various utility functions and classes."

# IMPORTS ########################################################### IMPORTS #

import datetime
import functools
import http.client
import json
import logging
import sqlite3
import time
import uuid

from flask import (abort, current_app, flash, g, jsonify, request, redirect,
                   session, url_for)
# import flask_mail
import jinja2.utils
import werkzeug.routing

from code_dds import constants

# CONFIG ############################################################# CONFIG #

# def init(app):
#     "Initialize the database; create logs table."
#     db = get_db(app)
#     with db:
#         db.execute("CREATE TABLE IF NOT EXISTS logs"
#                    "(iuid TEXT PRIMARY KEY,"
#                    " docid TEXT NOT NULL,"
#                    " added TEXT NOT NULL,"
#                    " updated TEXT NOT NULL,"
#                    " removed TEXT NOT NULL,"
#                    " username TEXT,"
#                    " remote_addr TEXT,"
#                    " user_agent TEXT,"
#                    " timestamp TEXT NOT NULL)")
#         db.execute("CREATE INDEX IF NOT EXISTS"
#                    " logs_docid_index ON logs (docid)")


# Global logger instance.
# _logger = None

# FUNCTIONS ####################################################### FUNCTIONS #

def get_logger():
    global _logger
    if _logger is None:
        config = current_app.config
        _logger = logging.getLogger(config["LOG_NAME"])
        if config["LOG_DEBUG"]:
            _logger.setLevel(logging.DEBUG)
        else:
            _logger.setLevel(logging.WARNING)
        if config["LOG_FILEPATH"]:
            if config["LOG_ROTATING"]:
                loghandler = logging.TimedRotatingFileHandler(
                    config["LOG_FILEPATH"],
                    when="midnight",
                    backupCount=config["LOG_ROTATING"])
            else:
                loghandler = logging.FileHandler(config["LOG_FILEPATH"])
        else:
            loghandler = logging.StreamHandler()
        loghandler.setFormatter(logging.Formatter(config["LOG_FORMAT"]))
        _logger.addHandler(loghandler)
    return _logger


def log_access(response):
    "Record access using the logger."
    if g.current_user:
        username = g.current_user["username"]
    else:
        username = None
    get_logger().debug(f"{request.remote_addr} {username}"
                       f" {request.method} {request.path}"
                       f" {response.status_code}")
    return response


# Global instance of mail interface.
# mail = flask_mail.Mail()


# Decorators for endpoints
def login_required(f):
    "Decorator for checking if logged in. Send to login page if not."
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not g.current_user:
            url = url_for("user.login", next=request.base_url)
            return redirect(url)
        return f(*args, **kwargs)
    return wrap


def admin_required(f):
    """Decorator for checking if logged in and 'admin' role.
    Otherwise return status 401 Unauthorized.
    """
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not g.am_admin:
            abort(http.client.UNAUTHORIZED)
        return f(*args, **kwargs)
    return wrap


class NameConverter(werkzeug.routing.BaseConverter):
    "URL route converter for a name."

    def to_python(self, value):
        if not constants.NAME_RX.match(value):
            raise werkzeug.routing.ValidationError
        return value.lower()    # Case-insensitive


class IuidConverter(werkzeug.routing.BaseConverter):
    "URL route converter for a IUID."

    def to_python(self, value):
        if not constants.IUID_RX.match(value):
            raise werkzeug.routing.ValidationError
        return value.lower()    # Case-insensitive


class Timer:
    "CPU timer."

    def __init__(self):
        self.start = time.process_time()

    def __call__(self):
        "Return CPU time (in seconds) since start of this timer."
        return time.process_time() - self.start

    @property
    def milliseconds(self):
        "Return CPU time (in milliseconds) since start of this timer."
        return round(1000 * self())


def get_iuid():
    "Return a new IUID, which is a UUID4 pseudo-random string."
    return uuid.uuid4().hex


def to_bool(s):
    "Convert string value into boolean."
    if not s:
        return False
    s = s.lower()
    return s in ("true", "t", "yes", "y")


def get_time(offset=None):
    """Current date and time (UTC) in ISO format, with millisecond precision.
    Add the specified offset in seconds, if given.
    """
    instant = datetime.datetime.utcnow()
    if offset:
        instant += datetime.timedelta(seconds=offset)
    instant = instant.isoformat()
    return instant[:17] + "{:06.3f}".format(float(instant[17:])) + "Z"


def url_for(endpoint, **values):
    "Same as 'flask.url_for', but with '_external' set to True."
    return url_for(endpoint, _external=True, **values)


def http_GET():
    "Is the HTTP method GET?"
    return request.method == "GET"


def http_POST(csrf=True):
    "Is the HTTP method POST? Check whether used for method tunneling."
    if request.method != "POST":
        return False
    if request.form.get("_http_method") in (None, "POST"):
        if csrf:
            check_csrf_token()
        return True
    else:
        return False


def http_PUT():
    "Is the HTTP method PUT? Is not tunneled."
    return request.method == "PUT"


def http_DELETE(csrf=True):
    "Is the HTTP method DELETE? Check for method tunneling."
    if request.method == "DELETE":
        return True
    if request.method == "POST":
        if csrf:
            check_csrf_token()
        return request.form.get("_http_method") == "DELETE"
    else:
        return False


def csrf_token():
    """Output HTML for cross-site request forgery (CSRF) protection."""
    # Generate a token to last the session's lifetime.
    if "_csrf_token" not in session:
        session["_csrf_token"] = get_iuid()
    html = '<input type="hidden" name="_csrf_token" value="%s">' % \
           session["_csrf_token"]
    return jinja2.utils.Markup(html)


def check_csrf_token():
    "Check the CSRF token for POST HTML."
    # Do not use up the token; keep it for the session's lifetime.
    token = session.get("_csrf_token", None)
    if not token or token != request.form.get("_csrf_token"):
        abort(http.client.BAD_REQUEST)


def flash_error(msg):
    "Flash error message."
    flash(str(msg), "error")


def flash_message(msg):
    "Flash information message."
    flash(str(msg), "message")


def thousands(value):
    "Template filter: Output integer with thousands delimiters."
    if isinstance(value, int):
        return "{:,}".format(value)
    else:
        return value


def accept_json():
    "Return True if the header Accept contains the JSON content type."
    acc = request.accept_mimetypes
    best = acc.best_match([constants.JSON_MIMETYPE, constants.HTML_MIMETYPE])
    return best == constants.JSON_MIMETYPE and \
        acc[best] > acc[constants.HTML_MIMETYPE]


def get_json(**data):
    "Return the JSON structure after fixing up for external representation."
    result = {"$id": request.url,
              "timestamp": get_time()}
    try:
        result["iuid"] = data.pop("_id")
    except KeyError:
        pass
    data.pop("_rev", None)
    data.pop("doctype", None)
    result.update(data)
    return result


def jsonify(result, schema_url=None):
    """Return a Response object containing the JSON of 'result'.
    Optionally add a header Link to the schema."""
    response = jsonify(result)
    if schema_url:
        response.headers.add("Link", schema_url, rel="schema")
    return response


def get_db(app=None):
    "Get the connection to the Sqlite3 database file."
    if app is None:
        app = current_app
    db = sqlite3.connect(app.config["SQLITE3_FILE"])
    db.row_factory = sqlite3.Row
    return db


def get_logs(docid):
    """Return the list of log entries for the given document identifier,
    sorted by reverse timestamp.
    """
    cursor = g.db.cursor()
    cursor.execute("SELECT added, updated, removed, username,"
                   " remote_addr, user_agent, timestamp"
                   " FROM logs WHERE docid=?"
                   " ORDER BY timestamp DESC", (docid,))
    result = []
    for row in cursor:
        item = dict(zip(row.keys(), row))
        item["added"] = json.loads(item["added"])
        item["updated"] = json.loads(item["updated"])
        item["removed"] = json.loads(item["removed"])
        result.append(item)
    return result
