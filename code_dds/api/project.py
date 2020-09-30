from flask import Blueprint, g, jsonify, request
from flask_restful import Resource, Api
import json
from code_dds.models import Project, File
from code_dds.marshmallows import project_schema, projects_schema
from code_dds import db


class ListProjects(Resource):
    def get(self):
        all_projects = Project.query.all()
        return projects_schema.dump(all_projects)


class ProjectFiles(Resource):
    def get(self, project):
        '''Get all files for a specific project

        Args:
            project:    Project ID

        Returns:
            List of files in db
        '''

        # Get all files belonging to project
        file_info = File.query.filter_by(project_id=project).all()

        # Return empty list if no files have been delivered
        if file_info is None:
            print("HERE", flush=True)
            return jsonify(message="There are no files in project",
                           files=[])

        files = {}
        for file in file_info:
            files[file.name] = {'id': file.id,
                                'directory_path': file.directory_path,
                                'size': file.size,
                                'compressed': file.compressed,
                                'public_key': file.public_key,
                                'salt': file.salt}

        return jsonify(message="", files=files)

        # query = f"""SELECT * FROM Files
        #         WHERE project_id='{project}'"""
        # print(f"query listing projects: {query}", flush=True)
        # try:
        #     cursor = g.db.cursor()
        # except:     # TODO: Fix exception
        #     pass
        # else:
        #     cursor.execute(query)

        #     for file in cursor:
        #         print(file, flush=True)
        #         files[file[1]] = {
        #             'directory_path': file[2],
        #             'size': file[3],
        #             'format': file[4],
        #             'compressed': True if file[5] == 1 else False,
        #             'public_key': file[6],
        #             'salt': file[7],
        #             'date_uploaded': file[8]
        #         }

        # return jsonify(files)


class DatabaseUpdate(Resource):
    def post(self):
        all_ = request.args

        try:
            new_file = File(
                name=all_['file'],
                directory_path=all_['directory_path'],
                size=int(all_['size']),
                format="",
                compressed=True if all_['ds_compressed'] else False,
                public_key=all_['key'], 
                salt=all_['salt'],
                project_id=int(all_['project'])
            )
        except Exception as e:
            return jsonify(updated=False, message=e)
        else:
            db.session.add(new_file)
            db.session.commit()

        return jsonify(updated=True, message="")
