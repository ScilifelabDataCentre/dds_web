"Site HTML endpoints."

import http.client
import os.path

import flask


blueprint = flask.Blueprint("site", __name__)


@blueprint.route("/static/<filename>")
def static(filename):
    "Static file for the site."
    dirpath = flask.current_app.config["SITE_STATIC_DIRPATH"]
    if not dirpath:
        raise ValueError("misconfiguration: no SITE_STATIC_DIRPATH set")
    dirpath = os.path.expandvars(os.path.expanduser(dirpath))
    if dirpath:
        return flask.send_from_directory(dirpath, filename)
    else:
        flask.abort(http.client.NOT_FOUND)
