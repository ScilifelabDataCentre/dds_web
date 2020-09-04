"About info HTMl endpoints."

import sqlite3
import sys

import flask
# import jsonschema

import code_dds
from code_dds import constants
from code_dds import utils


blueprint = flask.Blueprint("about", __name__)


@blueprint.route("/software")
def software():
    "Show software versions."
    return flask.render_template("about/software.html",
                                 software=get_software())


def get_software():
    v = sys.version_info
    return [
        (constants.SOURCE_NAME, code_dds.__version__, constants.SOURCE_URL),
        ("Python", f"{v.major}.{v.minor}.{v.micro}",
         "https://www.python.org/"),
        ("Flask", flask.__version__, "http://flask.pocoo.org/"),
        ("Sqlite3", sqlite3.version, "https://www.sqlite.org/index.html"),
        # ("jsonschema", jsonschema.__version__,
        #  "https://pypi.org/project/jsonschema"),
        ("Bootstrap", constants.BOOTSTRAP_VERSION, "https://getbootstrap.com/"),
        ("jQuery", constants.JQUERY_VERSION, "https://jquery.com/"),
        ("DataTables", constants.DATATABLES_VERSION, "https://datatables.net/"),
    ]


@blueprint.route("/settings")
@utils.admin_required
def settings():
    config = flask.current_app.config.copy()
    for key in ["SECRET_KEY", "MAIL_PASSWORD", "ADMIN_USER"]:
        if config.get(key):
            config[key] = "<hidden>"
    return flask.render_template("about/settings.html",
                                 items = sorted(config.items()))
