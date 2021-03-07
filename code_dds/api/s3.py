"""S3 module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import pathlib

# Installed
import flask_restful
import flask
import sqlalchemy
import json

# Own modules
from code_dds.api.user import token_required
from code_dds.db_code import models

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


class S3Info(flask_restful.Resource):
    """Gets the projects S3 keys"""
    method_decorators = [token_required]

    def get(self, current_user):
        """Get the safespring project"""

        # Get project ID
        project = flask.request.args
        if "project" not in project:
            return flask.make_response("Invalid request", 500)

        # Extra check for project access
        if project["project"] not in [x.id for x in current_user.user_projects]:
            return flask.make_response("Project access denied!", 401)

        # Get Safespring project
        try:
            # TODO (ina): Change -- these should not be saved in file
            s3path = pathlib.Path.cwd() / \
                pathlib.Path("sensitive/s3_config.json")
            with s3path.open(mode="r") as f:
                s3keys = json.load(f)["sfsp_keys"][current_user.safespring]
        except IOError as err:
            return flask.make_response(f"Failed getting keys! {err}", 500)

        # Get Safespring endpoint url
        try:
            with s3path.open(mode="r") as f:
                endpoint_url = json.load(f)["endpoint_url"]
        except IOError as err:
            return flask.make_response(f"Failed getting safespring url! {err}",
                                       500)

        if not all(x in s3keys for x in ["access_key", "secret_key"]):
            return flask.make_response("Keys not found!", 500)

        # Get bucket name
        try:
            bucket = models.Project.query.filter_by(id=project["project"]).\
                with_entities(models.Project.bucket).first()
        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(
                "Failed to get project bucket name! {err}", 500
            )
        
        if not bucket or bucket is None:
            return flask.make_response("Project bucket not found!", 500)


        return flask.jsonify({"safespring_project": current_user.safespring,
                              "keys": s3keys,
                              "url": endpoint_url,
                              "bucket": bucket[0]})
