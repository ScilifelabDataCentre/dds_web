from flask import Blueprint, g, request
from flask_restful import Resource, Api
import json


class Project(Resource):
    def post(self):
        # 
        id_ = request.form['id']
        return {'id': id_}
