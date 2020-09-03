""" Helper functions, classes and wrap calls

    Some functions are borrowed from anubis.utils
"""

import flask
import http.client
import uuid
import werkzeug.routing
from code_dds import constants


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


def get_iuid():
    """Return a new IUID, which is a UUID4 pseudo-random string."""
    return uuid.uuid4().hex


def is_method_get():
    """A wrapper call to check if the method is GET"""
    return flask.request.method == 'GET'


def is_method_put():
    """A wrapper call to check if the method is PUT"""
    return flask.request.method == 'PUT'


def is_method_post(csrf=True):
    """A wrapper call to check if the method is POST"""
    if flask.request.method != 'POST':
        return False
    if flask.request.form.get('_http_method') in (None, 'POST'):
        if csrf:
            check_csrf_token()
        return True
    else:
        return False


def is_method_delete(csrf=True):
    """A wrapper call to check if the method is DELETE"""
    if flask.request.method == 'DELETE':
        return True
    if flask.request.method == 'POST':
        if csrf:
            check_csrf_token()
        return flask.request.form.get('_http_method') == 'DELETE'
    else:
        return False


def get_csrf_token():
    """Output HTML for cross-site request forgery (CSRF) protection."""
    # Generate a token to last the session's lifetime.
    if '_csrf_token' not in flask.session:
        flask.session['_csrf_token'] = get_iuid()
    html = '<input type="hidden" name="_csrf_token" value="%s">' % \
           flask.session['_csrf_token']
    return jinja2.utils.Markup(html)


def check_csrf_token():
    """Check the CSRF token for POST HTML."""
    # Do not use up the token; keep it for the session's lifetime.
    token = flask.session.get('_csrf_token', None)
    if not token or token != flask.request.form.get('_csrf_token'):
        flask.abort(http.client.BAD_REQUEST)
