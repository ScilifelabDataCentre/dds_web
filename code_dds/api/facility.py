from flask import Blueprint, g, request, jsonify
from flask_restful import Resource, Api, fields, reqparse, marshal_with
import json

resource_fields = {
    'access': fields.Boolean,
    'user_id': fields.String,
    'project_id': fields.String,
    's3_id': fields.String,
    'error': fields.String
}


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
            return False, "", \
                "There is no recorded S3 project for the specified project"

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


def project_access(fac_id, project, owner):
    query = f"""SELECT delivery_option FROM Projects
            WHERE id='{project}' AND owner_='{owner}' AND facility='{fac_id}'"""
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
            return False, "The project doesn't exist or you don't have access"

        deliv_option = proj_found[0]
        if deliv_option != "S3":
            return False, "This project does not have S3 access"

    return True, ""


class FacilityInfo(object):
    def __init__(self, project_id, s3_id="", access=False, user_id="", error=""):
        print(f"within the facility info class. access: {access}, "
              f"user_id: {user_id}, project_id: {project_id}"
              f"s3_id: {s3_id}, error: {error}")
        self.access = access
        self.user_id = user_id
        self.project_id = project_id
        self.s3_id = s3_id
        self.error = error


class LoginFacility(Resource):
    @marshal_with(resource_fields)
    def get(self, username, password, project, owner):

        ok, fac_id = ds_access(username=username, password=password)
        if not ok:
            return FacilityInfo(project_id=project, user_id=fac_id,
                                error="Invalid credentials")

        ok, error = project_access(fac_id=fac_id,
                                   project=project, owner=owner)
        if not ok:
            return FacilityInfo(project_id=project, user_id=fac_id,
                                error=error)

        ok, s3_id, error = cloud_access(project=project)
        if not ok:
            return FacilityInfo(project_id=project, user_id=fac_id,
                                error=error, s3_id=s3_id)

        return FacilityInfo(access=True, project_id=project, s3_id=s3_id,
                            user_id=fac_id)


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
