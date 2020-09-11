from flask import Blueprint
from flask_restful import Api, Resource
from .user import LoginUser, LogoutUser, ListUsers
from .facility import LoginFacility, LogoutFacility, ListFacilities

api_blueprint = Blueprint('api_blueprint', __name__)
api = Api(api_blueprint)

api.add_resource(LoginUser, '/user/login/<string:username>/<string:password>',
                 endpoint='u_login')
api.add_resource(LoginFacility,
                 '/fac/login',
                 endpoint='f_login')
api.add_resource(LogoutUser, '/user/logout', endpoint='u_logout')
api.add_resource(LogoutFacility, '/fac/logout', endpoint='f_logout')
api.add_resource(ListUsers, '/listusers', endpoint='list_users')
api.add_resource(ListFacilities, '/listfacs', endpoint='list_facs')
