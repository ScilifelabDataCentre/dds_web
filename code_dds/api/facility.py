from flask import Blueprint, g, request, jsonify
from flask_restful import Resource, Api, fields
import json


def cloud_access(project):
    s3_query = f"""SELECT id FROM S3Projects
               WHERE project_s3='{project}'"""
    print(s3_query, flush=True)
    try:
        cursor = g.db.cursor()
    except:
        pass
    else:
        cursor.execute(s3_query)
        s3_id = cursor.fetchone()
        if s3_id is None:
            return {'project': project, 's3_id': '', 'error': 'There is no recorded S3 project for the specified project'}

        return {'project': project, 's3_id': s3_id[0], 'error': None}


def ds_access(username, password):
    query = f"""SELECT * FROM Facilities
            WHERE username='{username}' and password_='{password}'"""
    print(query, flush=True)
    try:
        cursor = g.db.cursor()
    except:
        pass
    else:
        cursor.execute(query)
        facility = cursor.fetchone()
        print(facility, flush=True)
        if facility is None:
            return False

        return True


def project_access(project, owner):
    query = f"""SELECT delivery_option FROM Projects
            WHERE id='{project}' and owner_='{owner}'"""
    print(query, flush=True)
    try:
        cursor = g.db.cursor()
    except:
        pass
    else:
        cursor.execute(query)
        proj_found = cursor.fetchone()
        print(proj_found, flush=True)
        if proj_found is None:
            return {'project': project, 'access': False,
                    'error': """The project doesn't exist or you
                             do not have access"""}

        deliv_option = proj_found[0]
        if deliv_option != "S3":
            return {'project': project, 'access': False,
                    'error': "This project does not have S3 access."}

    return {'project': project, 'access': True, 'error': None}


class LoginFacility(Resource):
    def get(self, username, password, project, owner):
        print(
            f"username: {username}, password: {password}, project: {project}", flush=True)

        if not ds_access(username=username, password=password):
            print("No DS access", flush=True)
            return jsonify({'access': False, 'error': "Invalid credentials"})

        proj_response = project_access(project=project, owner=owner)
        print(f"proj_response: {proj_response}", flush=True)
        if not proj_response['access']:
            return jsonify(proj_response)

        s3_access = cloud_access(project=project)
        print(f"s3_access: {s3_access}", flush=True)
        if s3_access == '':
            return jsonify({'access': False, **s3_access})

        return jsonify({'access': True, **s3_access})

    def post(self):
        # 1. Check if user exists - done
        # 2. Check if password is correct - done
        # 3. Check if allowed to post (role etc)? (probably not needed here atm)
        # 4. Get user id if ok - done
        # 5. Check if project exists - done
        # 6. Check if user has access to project
        # 7. Check delivery option
        # 8. Check S3 option
        # 9. Get S3 project id
        return {"class": "LoginFacility", "method": "post"}


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
