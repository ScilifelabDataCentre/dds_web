"About API endpoints."

import http.client

import flask

import code_dds.about
from code_dds import utils


blueprint = flask.Blueprint("api_about", __name__)

@blueprint.route("/software")
def software():
    result = [{"name": s[0], "version": s[1], "href": s[2]}
              for s in code_dds.about.get_software()]
    return utils.jsonify(utils.get_json(software=result),
                         schema_url=utils.url_for("api_schema.about_software"))
