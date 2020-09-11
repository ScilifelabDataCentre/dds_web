from flask import Blueprint, g
from flask_restful import Resource, Api
import json

# Create user_api blueprint
user_api = Blueprint('user_api', __name__)
api = Api(user_api)


class LoginFacility(Resource):
    def get(self):
        return {"class": "LoginFacility", "method": "get"}

    def post(self):
        return {"class": "LoginFacility", "method": "post"}


class LogoutFacility(Resource):
    def get(self):
        return {"class": "LogoutFacility", "method": "get"}

    def post(self):
        return {"class": "LogoutFacility", "method": "post"}


class ListFacilities(Resource):
    def get(self):
        try:
            cursor = g.db.cursor()
        except:
            pass
        else:
            cursor.execute("SELECT * FROM Facilities")
            facilities = cursor.fetchall()
            return facilities

    def post(self):
        return {"class": "ListFacilities", "method": "post"}
