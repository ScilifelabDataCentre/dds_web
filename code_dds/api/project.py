from flask import Blueprint, g, request
from flask_restful import Resource, Api
import json


class ProjectFiles(Resource):
    def get(self, project):
        query = f"""SELECT fileid FROM ProjectFiles
                WHERE projectid='{project}'"""

        try:
            cursor = g.db.cursor()
        except:     # TODO: Fix exception
            pass
        else:
            cursor.execute(query)
            
            all_files = cursor.fetchall()
            if all_files is None:
                return {"any?": False}
        
        return {"ok": True}
