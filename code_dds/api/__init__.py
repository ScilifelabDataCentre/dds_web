from flask import Blueprint
from flask_restful import Api, Resource
from .users import Login, Logout, ListUsers

api_blueprint = Blueprint('api_blueprint', __name__)
api = Api(api_blueprint)

api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Logout, '/logout', endpoint='logout')
api.add_resource(ListUsers, '/listusers', endpoint='list_users')
