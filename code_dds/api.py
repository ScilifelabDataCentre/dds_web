from flask import Blueprint
from flask_restful import Resource, Api


names = {"tim": {"age": 19, "gender": "male"},
         "bill": {"age": 70, "gender": "male"}}


class User(Resource):
    def get(self):
        return names


# blueprint = Blueprint("user", __name__, url_prefix="/user")
dds_api = Blueprint('api', __name__)
api = Api(dds_api)
api.add_resource(User, "/user", endpoint="user")
