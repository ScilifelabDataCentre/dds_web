from flask import Blueprint, g, request, jsonify, Response
from flask_restful import Resource, Api, fields, reqparse, marshal_with
from flask_sqlalchemy import SQLAlchemy
import json
from webargs import fields
from webargs.flaskparser import use_args

from code_dds.models import Facility, User, Project, S3Project
from code_dds.marshmallows import fac_schema, facs_schema
from code_dds import db


pw_fields = {
    'exists': fields.Boolean,
    'username': fields.String,
    'pw_settings': fields.String,
    'error': fields.String
}


def cloud_access(project):
    '''Gets the S3 project ID (bucket ID).

    Args:
        project:    Specified project ID used in current delivery

    Returns:
        tuple:  access, s3 project ID and error message
    '''

    s3_info = S3Project.query.filter_by(project_id=project).first()

    if s3_info is None:
        return False, "", "There is no recorded S3 project for the specified project"

    # Access granted, S3 ID and no error message
    return True, s3_info.id, ""


def ds_access(username, password):

    fac = Facility.query.filter_by(
        username=username, password=password).first()

    if fac is None:
        return False, ""

    return True, fac.id


def project_access(fac_id, project, owner) -> (bool, str):
    '''Checks the users access to the specified project

    Args:
        fac_id:     Facility ID
        project:    Project ID
        owner:      Owner ID

    Returns:
        tuple:  access and error message
    '''

    project_info = Project.query.filter_by(
        id=project, owner=owner, facility=fac_id).first()

    if project_info is None:
        return False, None, "The project doesn't exist or you don't have access"

    if project_info.delivery_option != "S3":
        return False, None, "The project does not have S3 access"

    # Check length of public key and quit if wrong
    # ---- here ----

    return True, project_info.public_key, ""


class PasswordSettings(Resource):

    def get(self, role, username):
        '''Checks database for user and returns password settings if found.

        Args:
            username:   The username wanting to get access

        Returns:
            json:
                exists:     True
                username:   Username
                settings:   Salt, length, n, r, p settings for pw
        '''

        if role == 'user':
            user = User.query.filter_by(username=username).first()
        elif role == 'fac':
            user = Facility.query.filter_by(username=username).first()

        if user is None:
            return jsonify(exists=False, error="The user does not exist",
                           username=username, settings="")

        return jsonify(exists=True, error="",
                       username=username, settings=user.settings)


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
            FacilityInfo with format resource_fields
        '''

        user_info = request.args

        # Look for user in database
        ok, fac_id = ds_access(username=user_info['username'],
                               password=user_info['password'])
        if not ok:  # Access denied
            return jsonify(access=DEFAULTS['access'], user_id=fac_id,
                           s3_id=DEFAULTS['s3_id'],
                           public_key=DEFAULTS['public_key'],
                           error="Invalid credentials",
                           project_id=user_info['project'])
        print("ds access ok", flush=True)

        # Look for project in database
        ok, public_key, error = project_access(fac_id=fac_id,
                                               project=user_info['project'],
                                               owner=user_info['owner'])
        if not ok:  # Access denied
            return jsonify(access=DEFAULTS['access'], user_id=fac_id,
                           s3_id=DEFAULTS['s3_id'],
                           public_key=DEFAULTS['public_key'],
                           error=error,
                           project_id=user_info['project'])
        print("project access ok", flush=True)

        # Get S3 project ID for project
        ok, s3_id, error = cloud_access(project=user_info['project'])
        if not ok:  # Access denied
            return jsonify(access=DEFAULTS['access'], user_id=fac_id,
                           s3_id=s3_id,
                           public_key=DEFAULTS['public_key'],
                           error=error,
                           project_id=user_info['project'])
        print("s3 access ok", flush=True)

        # Access approved
        return jsonify(access=True, user_id=fac_id,
                       s3_id=s3_id,
                       public_key=public_key,
                       error="Invalid credentials",
                       project_id=user_info['project'])


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
