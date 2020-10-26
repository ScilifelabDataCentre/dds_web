from flask import (Blueprint, g, make_response, session, request, jsonify,
                   current_app)
from flask_restful import Resource, Api, reqparse, abort

from code_dds.models import User

from code_dds.marshmallows import user_schema, users_schema
from code_dds.api.login import (
    ds_access, project_access, cloud_access, gen_access_token)


class LoginUser(Resource):
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

        Returns:
            json:   access (bool), s3_id (str), public_key (str),
                    error (str), project_id (int)
        '''

        # Get args from request
        user_info = request.args

        # Look for user in database
        ok, uid, error = ds_access(username=user_info['username'],
                                   password=user_info['password'],
                                   role=0)
        if not ok:  # Access denied
            return jsonify(access=DEFAULTS['access'],
                           user_id=uid,
                           s3_id=DEFAULTS['s3_id'],
                           public_key=DEFAULTS['public_key'],
                           error=error,
                           project_id=user_info['project'],
                           token="")

        # Look for project in database
        ok, public_key, error = project_access(uid=uid,
                                               project=user_info['project'],
                                               owner=uid)
        if not ok:  # Access denied
            return jsonify(access=DEFAULTS['access'],
                           user_id=uid,
                           s3_id=DEFAULTS['s3_id'],
                           public_key=DEFAULTS['public_key'],
                           error=error,
                           project_id=user_info['project'],
                           oken="")

        # Get S3 project ID for project
        ok, s3_id, error = cloud_access(project=user_info['project'])
        if not ok:  # Access denied
            return jsonify(access=DEFAULTS['access'],
                           user_id=uid,
                           s3_id=s3_id,
                           public_key=DEFAULTS['public_key'],
                           error=error,
                           project_id=user_info['project'],
                           token="")

        # Generate delivery token
        token = gen_access_token(project=user_info['project'])

        # Access approved
        return jsonify(access=True,
                       user_id=uid,
                       s3_id=s3_id,
                       public_key=public_key,
                       error="",
                       project_id=user_info['project'],
                       token=token)


class LogoutUser(Resource):
    def get(self):
        return {"class": "LogoutUser", "method": "get"}

    def post(self):
        return {"class": "LogoutUser", "method": "post"}


class ListUsers(Resource):
    def get(self):
        all_users = User.query.all()
        return users_schema.dump(all_users)

    def post(self):
        return {"class": "ListUsers", "method": "post"}
