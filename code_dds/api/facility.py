from flask import Blueprint, g, request
from flask_restful import Resource, Api
import json


class LoginFacility(Resource):
    def get(self):
        return {"class": "LoginFacility", "method": "get"}

    def post(self):
        # 1. Check if user exists
        # 2. Check if password is correct
        # 3. Check if allowed to post (role etc)? (probably not needed here atm)
        # 4. Get user id if ok 
        # 5. Check if project exists 
        # 6. Check if user has access to project
        # 7. Check if 
        username = request.form['username']
        password = request.form['password']
        query = """SELECT id FROM Facilities WHERE username=? and password_=?"""
        try:
            cursor = g.db.cursor()
        except:
            pass
        else: 
            cursor.execute(query, (username, 'ues'))
            facility = cursor.fetchone()
            return facility
        # return {"class": "LoginFacility", "method": "post"}


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
