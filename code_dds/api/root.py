"About API endpoints."

import http.client

import flask

from code_dds import utils


blueprint = flask.Blueprint("api", __name__)

@blueprint.route("")
def root():
    "API root."
    items = {
        "schema": {
            "root": {"href": utils.url_for("api_schema.root")},
            "logs": {"href": utils.url_for("api_schema.logs")},
            "user": {"href": utils.url_for("api_schema.user")},
            "users": {"href": utils.url_for("api_schema.users")},
            "about/software": {
                "href": utils.url_for("api_schema.about_software")
            }
        },
        "about": {
            "software": {"href": utils.url_for("api_about.software")}
        }
    }
    if flask.g.current_user:
        items["user"] = {
            "username": flask.g.current_user["username"],
            "href": utils.url_for("api_user.display",
                                  username=flask.g.current_user["username"])
        }
    if flask.g.am_admin:
        items["users"] = {
            "href": utils.url_for("api_user.all")
        }
    return utils.jsonify(utils.get_json(**items),
                         schema_url=utils.url_for("api_schema.root"))
