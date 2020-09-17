from flask import Blueprint, g, request, jsonify
from flask_restful import Resource, Api
import json


class ProjectFiles(Resource):
    def get(self, project):

        files = {}

        query = f"""SELECT * FROM Files
                WHERE id IN (SELECT fileid FROM ProjectFiles
                            WHERE projectid='{project}')"""

        try:
            cursor = g.db.cursor()
        except:     # TODO: Fix exception
            pass
        else:
            cursor.execute(query)

            for file in cursor:
                print(file, flush=True)
                files[file[1]] = {
                    'directory_path': file[2],
                    'size': file[3],
                    'format': file[4],
                    'compressed': True if file[5] == 1 else False,
                    'public_key': file[6],
                    'salt': file[7],
                    'date_uploaded': file[8]
                }

        return jsonify(files)
