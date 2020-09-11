from flask import Blueprint, g, make_response, session, request
from flask_restful import Resource, Api, reqparse, abort

# Create user_api blueprint
user_api = Blueprint('user_api', __name__)
api = Api(user_api)


class LoginUser(Resource):
    def get(self):
        try:
            cursor = g.db.cursor()
        except:
            pass    # Something wrong with db connection
        else:
            # table = """Users""" if method == "get" else """Facilities"""
            query_user = """SELECT * FROM Users"""
            # WHERE (username=?) AND (password_=?)"""

            # cursor.execute(query_user, (username, password))
            cursor.execute(query_user)
            user = cursor.fetchone()
            if user is None:
                pass  # The user doesn't exist in the database

            # id_ = user[0]

            # return {"id_": id_}
            return user

    def post(self):
        print(request.form['test'], flush=True)
        # print(request.args.get('test'), flush=True)
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
