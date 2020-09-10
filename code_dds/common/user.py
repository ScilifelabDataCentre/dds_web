from flask import Blueprint, g
from flask_restful import Resource, Api


class Login(Resource):
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


user_api = Blueprint('user_api', __name__)
api = Api(user_api)
api.add_resource(Login, "/login", endpoint="login")
