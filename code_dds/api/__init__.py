###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
import flask
import flask_restful

# Own modules
from code_dds.api import user
from code_dds.api import project
from code_dds.api import s3


###############################################################################
# BLUEPRINTS ##################################################### BLUEPRINTS #
###############################################################################

api_blueprint = flask.Blueprint("api_blueprint", __name__)
api = flask_restful.Api(api_blueprint)


###############################################################################
# RESOURCES ####################################################### RESOURCES #
###############################################################################

# Login/access ################################################# Login/access #
api.add_resource(user.AuthenticateUser, "/user/auth", endpoint="auth")
api.add_resource(project.ProjectAccess,
                 "/proj/auth", endpoint="proj_auth")

# 
api.add_resource(s3.S3Info, "/s3/proj", endpoint="proj_s3_info")

