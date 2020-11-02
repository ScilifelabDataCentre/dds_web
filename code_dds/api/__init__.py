"""REST API for the Data Delivery System"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
from flask import Blueprint
from flask_restful import Api
from flask_marshmallow import Marshmallow

# Own modules
from code_dds.api.user import LoginUser, ListUsers
from code_dds.api.facility import (LoginFacility, ListFacilities)
from code_dds.api.project import (ProjectFiles, ListProjects,
                                  ProjectKey)
from code_dds.api.files import ListFiles, FileSalt, DeliveryDate, FileUpdate
from code_dds.api.s3 import ListS3, S3Info


###############################################################################
# BLUEPRINTS ##################################################### BLUEPRINTS #
###############################################################################

api_blueprint = Blueprint('api_blueprint', __name__)
api = Api(api_blueprint)


###############################################################################
# RESOURCES ####################################################### RESOURCES #
###############################################################################

# Login/access
api.add_resource(LoginFacility, '/fac/login', endpoint='f_login')
api.add_resource(LoginUser, '/user/login', endpoint='u_login')

# List
api.add_resource(ListUsers, '/listusers', endpoint='list_users')
api.add_resource(ListFacilities, '/listfacs', endpoint='list_facs')
api.add_resource(ProjectFiles,
                 '/project/listfiles/<int:project>/<string:token>',
                 endpoint='project_files')
api.add_resource(ListFiles, '/listfiles', endpoint='list_files')
api.add_resource(ListS3, '/lists3', endpoint='list_s3')

# Delivery
api.add_resource(FileUpdate, '/project/updatefile', endpoint='update_file')
api.add_resource(FileSalt, '/file/salt/<int:file_id>', endpoint='file_salt')
api.add_resource(DeliveryDate, '/delivery/date/', endpoint='delivery_date')
api.add_resource(S3Info, '/s3info', endpoint="s3info")

# Key
api.add_resource(ProjectKey, '/project/<int:project>/key/<string:token>',
                 endpoint='key')
