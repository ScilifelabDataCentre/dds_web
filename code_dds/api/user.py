from flask import (Blueprint, g, make_response, session, request, jsonify,
                   current_app)
from flask_restful import Resource, Api, reqparse, abort
# from code_dds import db
# from api import my_schema, my_schemas
from code_dds.models import User

from code_dds import ma


class UserSchema(ma.Schema):
    class Meta:
        # The following fields will be shown when returned in request
        # Change for later -- hide sensitive info etc
        fields = ("id", "first_name", "last_name", "username", "password",
                  "settings", "email", "phone", "admin")


user_schema = UserSchema()
users_schema = UserSchema(many=True)


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

        # try:
        #     cur = g.db.cursor()
        # except:
        #     pass
        # else:
        #     cur.execute("SELECT * FROM Users")
        #     result = {}
        #     for (ID, Firstname, Lastname, Username, Password, Settings, Email, Phone) in cur:
        #         result[ID] = {"firstname": Firstname,
        #                       "lastname": Lastname,
        #                       "password": Password,
        #                       "settings": Settings,
        #                       "email": Email,
        #                       "phone": Phone}
        all_users = User.query.all()
        return users_schema.dump(all_users)

    def post(self):
        return {"class": "ListUsers", "method": "post"}
