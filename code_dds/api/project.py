from flask import Blueprint, g, jsonify, request
from flask_restful import Resource, Api
import json
from code_dds.models import Project
from code_dds.marshmallows import project_schema, projects_schema


class ListProjects(Resource):
    def get(self):
        all_projects = Project.query.all()
        return projects_schema.dump(all_projects)


class ProjectFiles(Resource):
    def get(self, project):

        files = {}

        query = f"""SELECT * FROM Files
                WHERE project_id='{project}'"""
        print(f"query listing projects: {query}", flush=True)
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


class DatabaseUpdate(Resource):
    def post(self):
        db_changed = False
        # 1. Check if exists
        # 2. If exists -- update, otherwise create
        print("HEELLOOOO", flush=True)
        all_ = request.form
        print(f"all: {all_}", flush=True)
        # project = request.form
        # file = request.form['file']
        # print(f"file: {file}", flush=True)
        query = f"""SELECT id FROM Files
                WHERE name_='{all_['file']}'"""
        try:
            cursor = g.db.cursor()
        except:     # TODO: Fix execption
            pass
        else:
            cursor.execute(query)

            all_files = cursor.fetchall()
            if len(all_files) == 0:
                # The file is not in the database --> create
                insert_query = \
                    f"""INSERT INTO Files (name_, directory_path, size,
                                           format_, compressed, public_key,
                                           salt, date_uploaded, project_id)
                        VALUES ('{all_["file"]}', '{all_["directory_path"]}',
                                '{all_["size"]}', 'format?',
                                '{1 if all_["ds_compressed"] else 0}', 
                                '{all_["key"]}', '{all_["salt"]}', NOW(), 
                                '{all_["project"]}');"""
                try:
                    cursor.execute(insert_query)
                    g.db.commit()
                except Exception as e:  # TODO: Fix exception
                    print(e, flush=True)
                else:
                    db_changed = True

            elif len(all_files) > 1:

                pass    # There are multiple files, should not be possible --> error
            else:
                update_query = \
                    f"""UPDATE Files
                    SET 
                    directory_path='{all_["directory_path"]}', 
                    size='{all_["size"]}', 
                    compressed='{1 if all_["ds_compressed"] else 0}', 
                    public_key='{all_["key"]}',
                    salt='{all_["salt"]}', 
                    date_uploaded=NOW(), 
                    project_id='{all_["project"]}'
                    WHERE id=all_files[0]
                    """
                try:
                    cursor.execute(update_query)
                    g.db.commit()
                except Exception as e:  # TODO: Fix exception
                    print(e, flush=True)
                else:
                    db_changed = True
        return db_changed
