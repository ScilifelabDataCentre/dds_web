"Web app template."

import flask
import jinja2

import mariadb

import code_dds.about
import code_dds.config
import code_dds.user
import code_dds.site
# To be developed.
# import code_dds.entity

import code_dds.api.about
import code_dds.api.root
import code_dds.api.schema
import code_dds.api.user
from code_dds import constants
from code_dds import utils

app = flask.Flask(__name__)

# Add URL map converters.
app.url_map.converters["name"] = utils.NameConverter
app.url_map.converters["iuid"] = utils.IuidConverter

# Get the configuration, and initialize modules (database).
code_dds.config.init(app)
# utils.init(app)
# code_dds.user.init(app)
# utils.mail.init_app(app)

# Add template filters.
app.add_template_filter(utils.thousands)


@app.context_processor
def setup_template_context():
    "Add useful stuff to the global context of Jinja2 templates."
    return dict(constants=constants,
                csrf_token=utils.csrf_token)


@app.before_request
def prepare():
    "Open the database connection; get the current user."
    flask.g.db = mariadb.connect(**app.config['DB'])
    flask.g.current_user = "tester"
    # flask.g.am_admin = flask.g.current_user and \
    #     flask.g.current_user["role"] == constants.ADMIN


# app.after_request(utils.log_access)


@app.route("/")
def home():
    "Home page. Redirect to API root if JSON is accepted."
    if utils.accept_json():
        return flask.redirect(flask.url_for("api_root"))
    else:
        return flask.render_template("home.html")


@app.route("/debug")
@utils.admin_required
def debug():
    "Return some debug info for admin."
    result = [f"<h1>Debug  {constants.VERSION}</h2>"]
    result.append("<h2>headers</h2>")
    result.append("<table>")
    for key, value in sorted(flask.request.headers.items()):
        result.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
    result.append("</table>")
    result.append("<h2>environ</h2>")
    result.append("<table>")
    for key, value in sorted(flask.request.environ.items()):
        result.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
    result.append("</table>")
    return jinja2.utils.Markup("\n".join(result))


# Set up the URL map.
app.register_blueprint(code_dds.about.blueprint, url_prefix="/about")
app.register_blueprint(code_dds.user.blueprint, url_prefix="/user")
app.register_blueprint(code_dds.site.blueprint, url_prefix="/site")
# To be developed.
# app.register_blueprint(code_dds.entity.blueprint, url_prefix="/entity")

app.register_blueprint(code_dds.api.root.blueprint, url_prefix="/api")
app.register_blueprint(code_dds.api.about.blueprint, url_prefix="/api/about")
app.register_blueprint(code_dds.api.schema.blueprint, url_prefix="/api/schema")
app.register_blueprint(code_dds.api.user.blueprint, url_prefix="/api/user")
# To be developed
# app.register_blueprint(code_dds.api.entity.blueprint, url_prefix="/api/entity")


# This code is used only during development.
if __name__ == "__main__":
    app.run(host=app.config["SERVER_HOST"],
            port=app.config["SERVER_PORT"])
