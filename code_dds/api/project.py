"""Project module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import functools

# Installed
import flask_restful
import flask
import sqlalchemy
import pathlib
import json
import boto3
import botocore

# Own modules
from code_dds import db
from code_dds.api.user import jwt_token
from code_dds.api.user import is_facility
from code_dds.common.db_code import models
from code_dds import timestamp
from code_dds.api.api_s3_connector import ApiS3Connector
from code_dds.api.db_connector import DBConnector
from code_dds.api.dds_decorators import token_required, project_access_required


###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################


class ProjectAccess(flask_restful.Resource):
    """Checks a users access to a specific project."""
    method_decorators = [token_required]

    def get(self, current_user, project):
        """Checks the users access to a specific project and action."""
        args = flask.request.args

        # Deny access if project or method not specified
        if "method" not in args:
            return flask.make_response("Invalid request", 500)

        # Check if user is allowed to performed attempted operation
        user_is_fac, error = is_facility(username=current_user.username)
        if user_is_fac is None:
            return flask.make_response(error, 401)

        # Facilities can upload and list, users can download and list
        # TODO (ina): Add allowed actions to DB instead of hard coding
        if (user_is_fac and args["method"] not in ["put", "ls", "rm"]) or \
                (not user_is_fac and args["method"] not in ["get", "ls", "rm"]):
            return flask.make_response(
                f"Attempted to {args['method']} in project {project['id']}. "
                "Permission denied.", 401
            )

        # Check if user has access to project
        if project["id"] in [x.id for x in current_user.user_projects]:
            token, error = jwt_token(user_id=current_user.public_id,
                                     is_fac=user_is_fac, project_id=project["id"],
                                     project_access=True)
            if token is None:
                return flask.make_response(error, 500)

            return flask.jsonify({"dds-access-granted": True, "token": token.decode("UTF-8")})

        return flask.make_response("Project access denied", 401)


class UserProjects(flask_restful.Resource):
    """Gets all projects registered to a specific user."""
    method_decorators = [token_required]

    def get(self, current_user, *args):
        """Get info regarding all projects which user is involved in."""

        # TODO: Return different things depending on if facility or not
        user_is_fac, error = is_facility(username=current_user.username)
        if user_is_fac is None:
            return flask.make_response(error, 401)

        all_projects = list()
        columns = ["Project ID", "Title", "PI", "Status", "Last updated"]
        for x in current_user.user_projects:
            all_projects.append({columns[0]: x.id,
                                 columns[1]: x.title,
                                 columns[2]: x.pi,
                                 columns[3]: x.status,
                                 columns[4]: timestamp(
                                     datetime_string=x.date_updated
            )}
            )
        return flask.jsonify({"all_projects": all_projects, "columns": columns})


class RemoveContents(flask_restful.Resource):
    """Removes all project contents."""
    method_decorators = [project_access_required, token_required]

    def delete(self, _, project):
        """Removes all project contents."""

        # Delete files
        removed, error = (False, "")
        with DBConnector() as dbconn:
            removed, error = dbconn.delete_all()

            # Return error if contents not deleted from db
            if not removed:
                return flask.make_response(error, 500)

            # Delete from bucket
            with ApiS3Connector() as s3conn:
                if None in [s3conn.url, s3conn.keys, s3conn.bucketname]:
                    return flask.make_response(
                        "No s3 info returned! " + s3conn.message, 500
                    )

                removed, error = s3conn.remove_all()

                # Return error if contents not deleted from s3 bucket
                if not removed:
                    db.session.rollback()
                    return flask.make_response(error, 500)

                # Commit changes to db
                try:
                    db.session.commit()
                except sqlalchemy.exc.SQLAlchemyError as err:
                    return flask.make_response(str(err), 500)

        return flask.jsonify({"removed": removed, "error": error})
