"Web API for Data Delivery System"

# IMPORTS ########################################################### IMPORTS #

# Standard library

# Installed
from flask import render_template

# Own modules
from code_dds import create_app
from code_dds.api import api_blueprint

# CONFIG ############################################################# CONFIG #

app = create_app()


# BLUEPRINTS ##################################################### BLUEPRINTS #

app.register_blueprint(api_blueprint, url_prefix='/api/v1')


# HOME ROUTE ##################################################### HOME ROUTE #



# INITIATE ######################################################### INITIATE #
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


# NOT USED ######################################################### NOT USED #

# The code below is no longer needed due to the new config setup

# CONFIG ############################################################# CONFIG #

# app = Flask(__name__)

# URL map converters - "xxx" will result in that xxx can be used in @app.route
# app.url_map.converters["name"] = utils.NameConverter
# app.url_map.converters["iuid"] = utils.IuidConverter

# # Get and initialize app configuration
# config.init(app)

# # Add template filters - "converts" integers with thousands delimiters
# app.add_template_filter(utils.thousands)

# Context processors injects new variables automatically into the context of a
# # template. Runs before the template is rendered.
# # Returns a dictionary. Keys and values are merged with the template context
# # for all templates in the app. In this case: the constants and the function
# # csrf_token.

# @app.context_processor
# def setup_template_context():
#     "Add useful stuff to the global context of Jinja2 templates."
#     return dict(constants=constants,
#                 csrf_token=utils.csrf_token)


# # Registers a function to run before >>each<< request
# @app.before_request
# def prepare():
#     "Open the database connection; get the current user."
#     g.db = mariadb.connect(**app.config['DB'])
#     g.current_user = "tester"
