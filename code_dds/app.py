# "Web app template."

# # IMPORTS ########################################################### IMPORTS #

# # Standard library

# # Installed
# from flask import (Flask, g, redirect, render_template,
#                    request, url_for, flash)
# from flask_restful import Api, Resource
# import jinja2
# import mariadb
# import logging
# # Own modules
# from code_dds import constants
# from code_dds import utils

# from code_dds import user
# from code_dds import config

# from code_dds.api import api_blueprint

# # CONFIG ############################################################# CONFIG #

# app = Flask(__name__)

# # URL map converters - "xxx" will result in that xxx can be used in @app.route
# app.url_map.converters["name"] = utils.NameConverter
# app.url_map.converters["iuid"] = utils.IuidConverter

# # Get and initialize app configuration
# config.init(app)

# # Add template filters - "converts" integers with thousands delimiters
# app.add_template_filter(utils.thousands)


# # add_resource(resource, *urls, **kwargs)
# # endpoint -- endpoint name --> can be used to reference the route in fields.Url fields
# # add_resource(HelloWorld, "/helloworld/<string:name>")
# app.register_blueprint(api_blueprint, url_prefix='/api/v1')

# # Context processors injects new variables automatically into the context of a
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

# # app.after_request(utils.log_access)


# @app.route("/")
# def home():
#     """Home page."""
#     return render_template("home.html")


# # This code is used only during development.
# if __name__ == "__main__":
#     app.run(host=app.config["SERVER_HOST"],
#             port=app.config["SERVER_PORT"])

"""App entry point."""
from code_dds import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
