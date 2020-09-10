from flask import Blueprint, g
from flask_restful import Resource, Api

# Create user_api blueprint
user_api = Blueprint('user_api', __name__)
api = Api(user_api)


# @api.resource('/login', endpoint="login")
class Login(Resource):
    def get(self):
        return {"class": "Login", "method": "get"}

    def post(self):
        return {"class": "Login", "method": "post"}


# @api.resource('/logout', endpoint="logout")
class Logout(Resource):
    def get(self):
        return {"class": "Logout", "method": "get"}

    def post(self):
        return {"class": "Logout", "method": "post"}


# @api.resource('/listusers', endpoint="list_users")
class ListUsers(Resource):
    def get(self):
        try:
            cur = g.db.cursor()
        except:
            pass
        else:
            cur.execute("SELECT * FROM Users")
            result = {}
            for (ID, Firstname, Lastname, Username, Password, Settings, Email, Phone) in cur:
                result[ID] = {"firstname": Firstname,
                              "lastname": Lastname,
                              "password": Password,
                              "settings": Settings,
                              "email": Email,
                              "phone": Phone}

            return result

    def post(self):
        return {"class": "ListUsers", "method": "post"}
