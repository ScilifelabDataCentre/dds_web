from flask import Blueprint, g
from flask_restful import Resource, Api
import json

# Create user_api blueprint
user_api = Blueprint('user_api', __name__)
api = Api(user_api)


class LoginUser(Resource):
    def get(self, username, password):
        try:
            cursor = g.db.cursor()
        except:
            pass    # Something wrong with db connection
        else:
            cursor.execute(
                "SELECT * FROM Users WHERE (Username=?) AND (Password=?)", (username, password)
            )

            user = cursor.fetchone()
            if user is None:
                pass  # The user doesn't exist in the database

            return user

    def post(self):
        return {"class": "LoginUser", "method": "post"}


class LogoutUser(Resource):
    def get(self):
        return {"class": "LogoutUser", "method": "get"}

    def post(self):
        return {"class": "LogoutUser", "method": "post"}


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
