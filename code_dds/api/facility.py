from flask import Blueprint, g, request, jsonify, Response
from flask_restful import Resource, Api, fields, reqparse, marshal_with
import json
from webargs import fields
from webargs.flaskparser import use_args


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

    # Specify database query
    s3_query = f"""SELECT id FROM S3Projects
               WHERE project_s3='{project}'"""

    # Execute query
    try:
        cursor = g.db.cursor()
    except:     # TODO: Fix exception
        pass
    else:
        cursor.execute(s3_query)    # Execute

        # Should be only one S3 ID --> get one
        s3_id = cursor.fetchone()
        if s3_id is None:
            return False, "", \
                "There is no recorded S3 project for the specified project"

        # Access granted, S3 ID and no error message
        return True, s3_id[0], ""


def ds_access(username, password):
    query = f"""SELECT id FROM Facilities
            WHERE username='{username}' and password_='{password}'"""
    print(f"ds_access query: {query}", flush=True)
    try:
        cursor = g.db.cursor()
    except:
        pass
    else:
        cursor.execute(query)
        facility = cursor.fetchone()
        print(f"ds_access result: {facility}", flush=True)
        # return facility
        if facility is None:
            return False, ''

        return True, facility[0]


def project_access(fac_id, project, owner) -> (bool, str):
    '''Checks the users access to the specified project

    Args:
        fac_id:     Facility ID
        project:    Project ID
        owner:      Owner ID

    Returns:
        tuple:  access and error message
    '''

    # Specify query
    query = f"""SELECT delivery_option, public_key FROM Projects
            WHERE id='{project}' AND owner_='{owner}' AND facility='{fac_id}'"""

    # Execute query
    try:
        cursor = g.db.cursor()  # Connection is performed at beginning of req
    except:     # TODO: Fix exception
        pass
    else:
        cursor.execute(query)   # Execute

        # Should be only one project --> fetch only one
        proj_found = cursor.fetchone()
        if proj_found is None:
            return False, None, "The project doesn't exist" \
                "or you don't have access"

        # Quit if project delivery option is not S3
        deliv_option = proj_found[0]
        if deliv_option != "S3":
            return False, None, "This project does not have S3 access"

        public_key = proj_found[1]
        if public_key is None:
            return False, public_key, "The project does not have a public key"

        # Access granted and no error
        return True, public_key, ""


class PasswordSettings(Resource):

    def get(self, username):
        '''Checks database for user and returns password settings if found.

        Args:
            username:   The username wanting to get access

        Returns:
            json:
                exists:     True
                username:   Username
                settings:   Salt, length, n, r, p settings for pw
        '''

        # Get password settings if the user exists
        pw_query = f"""SELECT settings FROM Facilities
                       WHERE username='{username}'"""
        try:
            cursor = g.db.cursor()
        except:     # TODO: Fix exception
            pass
        else:
            # Execute query
            cursor.execute(pw_query)

            # Fetch result
            pw_settings = cursor.fetchone()

            # If result is empty the user does not exist, otherwise return
            # password settings
            if pw_settings is None:
                return jsonify({'exists': False, 'username': username,
                                'settings': "", 'error': "The user does not exist"})  # The user doesn't exist
            else:
                return jsonify({'exists': True, 'username': username,
                                'settings': pw_settings[0], 'error': ""})


# login_fields = {
#     'access': fields.Boolean,
#     'user_id': fields.String,
#     'project_id': fields.String,
#     's3_id': fields.String,
#     'public_key': fields.String,
#     'error': fields.String
# }


# class FacilityInfo(object):
#     def __init__(self, project_id, s3_id="", access=False, user_id="",
#                  public_key="", error=""):
#         '''Sets the values for common format for login response with
#         resource_fields.

#         Args:
#             project_id:     Project ID
#             s3_id:          The S3 project ID used for the current project
#             access:         True if access to DS granted
#             user_id:        ID of approved user, "" if not granted
#             error:          Error message, "" if no error

#         Attributes:
#             Same as args.
#         '''

#         self.access = access
#         self.user_id = user_id
#         self.project_id = project_id
#         self.s3_id = s3_id
#         self.error = error
#         self.public_key = public_key


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

        # return {'access': False}
        # Look for user in database
        ok, fac_id = ds_access(username=user_info['username'],
                               password=user_info['password'])
        if not ok:  # Access denied
            return jsonify(access=DEFAULTS['access'], user_id=fac_id,
                           s3_id=DEFAULTS['s3_id'],
                           public_key=DEFAULTS['public_key'],
                           error="Invalid credentials",
                           project_id=user_info['project'])

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

        # Get S3 project ID for project
        ok, s3_id, error = cloud_access(project=user_info['project'])
        if not ok:  # Access denied
            return jsonify(access=DEFAULTS['access'], user_id=fac_id,
                           s3_id=s3_id,
                           public_key=DEFAULTS['public_key'],
                           error=error,
                           project_id=user_info['project'])

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
