"""REST API for the Data Delivery System"""

# IMPORTS ########################################################### IMPORTS #

# Standard library

# Installed
from flask import Blueprint
from flask_restful import Api

# Own modules
from .user import LoginUser, ListUsers
from .facility import (LoginFacility, ListFacilities,
                       PasswordSettings)
from .project import ProjectFiles, DatabaseUpdate

api_blueprint = Blueprint('api_blueprint', __name__)
api = Api(api_blueprint)

# Login/access
api.add_resource(PasswordSettings, '/pw_settings/<string:role>/<string:username>', endpoint='pw_settings')
api.add_resource(LoginFacility, '/fac/login', endpoint='f_login')
api.add_resource(LoginUser, '/user/login', endpoint='u_login')

# api.add_resource(LogoutUser, '/user/logout', endpoint='u_logout')
# api.add_resource(LogoutFacility, '/fac/logout', endpoint='f_logout')

# List
api.add_resource(ListUsers, '/listusers', endpoint='list_users')
api.add_resource(ListFacilities, '/listfacs', endpoint='list_facs')
api.add_resource(ProjectFiles, '/project/listfiles/<string:project>', endpoint='project_files')

# Delivery
api.add_resource(DatabaseUpdate, '/project/updatefile', endpoint='update_file')
