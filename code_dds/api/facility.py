from flask import Blueprint, g, request, jsonify, Response
from flask_restful import Resource, Api, fields, reqparse, marshal_with
from flask_sqlalchemy import SQLAlchemy
import json
from webargs import fields
from webargs.flaskparser import use_args

from code_dds.marshmallows import fac_schema, facs_schema
from code_dds import db
from code_dds.api.login import (
    ds_access, project_access, cloud_access, gen_access_token)


class LoginFacility(Resource):

    global DEFAULTS
    DEFAULTS = {
        'access': False,
        'user_id': "",
        's3_id': "",
        'public_key': None,
        'error': ""
    }

    # @marshal_with(login_fields)  # Worked first but stopped working for some
    # reason. Gives response 500.
    def post(self):
        '''Checks the users access to the delivery system.

        Args:
            username:   Username
            password:   Password
            project:    Project ID
            owner:      Owner of project with project ID

        Returns:
            json:   access (bool), s3_id (str), public_key (str),
                    error (str), project_id (int)

        '''

        # Get args from request
        user_info = request.args

        # Look for user in database
        ok, fac_id, error = ds_access(username=user_info['username'],
                                      password=user_info['password'],
                                      role=1)
        if not ok:  # Access denied
            return jsonify(access=DEFAULTS['access'],
                           user_id=fac_id,
                           s3_id=DEFAULTS['s3_id'],
                           public_key=DEFAULTS['public_key'],
                           error=error,
                           project_id=user_info['project'],
                           token="")

        # Look for project in database
        ok, public_key, error = project_access(uid=fac_id,
                                               project=user_info['project'],
                                               owner=user_info['owner'])
        if not ok:  # Access denied
            return jsonify(access=DEFAULTS['access'],
                           user_id=fac_id,
                           s3_id=DEFAULTS['s3_id'],
                           public_key=DEFAULTS['public_key'],
                           error=error,
                           project_id=user_info['project'],
                           token="")

        # Get S3 project ID for project
        ok, s3_id, error = cloud_access(project=user_info['project'])
        if not ok:  # Access denied
            return jsonify(access=DEFAULTS['access'],
                           user_id=fac_id,
                           s3_id=s3_id,
                           public_key=DEFAULTS['public_key'],
                           error=error,
                           project_id=user_info['project'],
                           token="")

        # Generate delivery token
        token = gen_access_token(project=user_info['project'])

        # Access approved
        return jsonify(access=True,
                       user_id=fac_id,
                       s3_id=s3_id,
                       public_key=public_key,
                       error="",
                       project_id=user_info['project'],
                       token=token)


class LogoutFacility(Resource):
    def get(self):
        return {"class": "LogoutFacility", "method": "get"}

    def post(self):
        return {"class": "LogoutFacility", "method": "post"}


class ListFacilities(Resource):
    def get(self):
        all_facilities = Facility.query.all()
        return facs_schema.dump(all_facilities)

    def post(self):
        return {"class": "ListFacilities", "method": "post"}
