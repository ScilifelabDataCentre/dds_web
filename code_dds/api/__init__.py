"""REST API for the Data Delivery System"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
import flask
import flask_restful
import flask_marshmallow

# Own modules
from code_dds.api import facility
from code_dds.api import files
from code_dds.api import project
from code_dds.api import s3
from code_dds.api import user


###############################################################################
# BLUEPRINTS ##################################################### BLUEPRINTS #
###############################################################################

api_blueprint = flask.Blueprint("api_blueprint", __name__)
api = flask_restful.Api(api_blueprint)


###############################################################################
# RESOURCES ####################################################### RESOURCES #
###############################################################################

# Login/access ################################################# Login/access #
api.add_resource(user.LoginUser, "/user/login", endpoint="u_login")  # params

# List ################################################################# List #
# Development only
api.add_resource(user.ListUsers, "/listusers", endpoint="list_users")
api.add_resource(facility.ListFacilities, "/listfacs", endpoint="list_facs")
api.add_resource(files.ListFiles, "/listfiles", endpoint="list_files")
api.add_resource(s3.ListS3, "/lists3", endpoint="list_s3")

# Used
api.add_resource(project.ProjectFiles, "/project/<string:proj_id>/listfiles",
                 endpoint="project_files")  # args & params

# Delivery ######################################################### Delivery #
# Update db
api.add_resource(files.FileUpdate, "/updatefile",
                 endpoint="update_file")    # params
api.add_resource(files.DeliveryDate, "/delivery/date/",
                 endpoint="delivery_date")  # params

# Get info
api.add_resource(s3.S3Info, "/s3info", endpoint="s3info") # atm no args

# Key
api.add_resource(project.ProjectKey, "/project/<string:project>/key",
                 endpoint="key")  # args & params
