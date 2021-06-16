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
from sqlalchemy.sql import func
from cryptography.hazmat.primitives.kdf import scrypt
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_decrypt as decrypt
from cryptography.hazmat import backends


# Own modules
from dds_web import app, db, timestamp
from dds_web.api.user import jwt_token
from dds_web.database import models
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.db_connector import DBConnector
from dds_web.api.dds_decorators import token_required, project_access_required


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
            app.logger.debug("No method in request.")
            return flask.make_response("Invalid request.", 500)

        # Check if project id specified
        if project["id"] is None:
            app.logger.debug("No project retrieved from token.")
            return flask.make_response("No project specified.", 401)

        # Check if project exists
        app.logger.debug("Getting project from db.")
        try:
            attempted_project = models.Project.query.filter(
                models.Project.public_id == func.binary(project["id"])
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            return flask.make_response(f"Database connection failed: {sqlerr}", 500)

        if not attempted_project:
            return flask.make_response(f"Project does not exist: {project['id']}", 401)

        # Check if attempted action is ok for user
        app.logger.debug(
            "User permissions: %s, attempted method: %s", current_user.permissions, args["method"]
        )
        permissions_dict = {"get": "g", "ls": "l", "put": "p", "rm": "r"}
        if permissions_dict[args["method"]] not in list(current_user.permissions):
            return flask.make_response(
                f"Attempted to '{args['method']}' in project '{project['id']}'. Permission denied.",
                401,
            )

        # Check if user has access to project
        app.logger.debug("User projects: %s", current_user.projects)
        if project["id"] in [x.public_id for x in current_user.projects]:
            app.logger.debug("Updating token...")
            token, error = jwt_token(
                username=current_user.username,
                project_id=project["id"],
                project_access=True,
                permission=args["method"],
            )
            if token is None:
                return flask.make_response(error, 500)

            # Project access granted
            return flask.jsonify(
                {
                    "dds-access-granted": True,
                    "token": token.decode("UTF-8"),
                }
            )

        # Project access denied
        return flask.make_response("Project access denied", 401)


class GetPublic(flask_restful.Resource):
    """Gets the public key beloning to the current project."""

    method_decorators = [project_access_required, token_required]

    def get(self, _, project):
        """Get public key from database."""

        app.logger.debug("Getting the public key.")
        try:
            proj_pub = (
                models.Project.query.filter_by(public_id=project["id"])
                .with_entities(models.Project.public_key)
                .first()
            )

            if not proj_pub:
                return flask.make_response("No public key found.", 500)

        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(str(err), 500)
        else:
            return flask.jsonify({"public": proj_pub[0]})


class GetPrivate(flask_restful.Resource):
    """Gets the private key belonging to the current project."""

    method_decorators = [project_access_required, token_required]

    def get(self, _, project):
        """Get private key from database"""

        # TODO (ina): Change handling of private key -- not secure
        app.logger.debug("Getting the private key.")
        try:
            proj_priv = (
                models.Project.query.filter_by(public_id=project["id"])
                .with_entities(
                    models.Project.private_key,
                    models.Project.privkey_nonce,
                    models.Project.privkey_salt,
                )
                .first()
            )
        except sqlalchemy.exc.SQLAlchemyError as err:
            return flask.make_response(str(err), 500)
        else:
            app_secret = app.config["SECRET_KEY"]
            passphrase = app_secret.encode("utf-8")

            enc_key = bytes.fromhex(proj_priv[0])
            nonce = bytes.fromhex(proj_priv[1])
            salt = bytes.fromhex(proj_priv[2])

            kdf = scrypt.Scrypt(
                salt=salt,
                length=32,
                n=2 ** 14,
                r=8,
                p=1,
                backend=backends.default_backend(),
            )

            key_enc_key = kdf.derive(passphrase)
            try:
                decrypted_key = decrypt(ciphertext=enc_key, aad=None, nonce=nonce, key=key_enc_key)
            except Exception as err:
                app.logger.exception(err)
                return flask.make_response(str(err), 500)

            # print(f"Decrypted key: {decrypted_key}", flush=True)

            return flask.jsonify({"private": decrypted_key.hex().upper()})


class UserProjects(flask_restful.Resource):
    """Gets all projects registered to a specific user."""

    method_decorators = [token_required]

    def get(self, current_user, project, *args):
        """Get info regarding all projects which user is involved in."""

        if project["permission"] != "ls":
            return flask.make_response(
                f"User {current_user.username} does not have permission to view projects.", 401
            )

        # TODO: Return different things depending on if facility or not
        columns = ["Project ID", "Title", "PI", "Status", "Last updated"]
        all_projects = [
            {
                columns[0]: x.public_id,
                columns[1]: x.title,
                columns[2]: x.pi,
                columns[3]: x.status,
                columns[4]: timestamp(
                    datetime_string=x.date_updated if x.date_updated else x.date_created
                ),
            }
            for x in current_user.projects
        ]
        app.logger.debug(all_projects)
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
                    return flask.make_response("No s3 info returned! " + s3conn.message, 500)

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


class UpdateProjectSize(flask_restful.Resource):

    method_decorators = [project_access_required, token_required]

    def put(self, _, project):
        """Update the project size and updated time stamp."""

        updated, error = (False, "")
        current_try, max_tries = (1, 5)
        while current_try < max_tries:
            try:
                current_project = models.Project.query.filter(
                    models.Project.public_id == func.binary(project["id"])
                ).first()

                tot_file_size = (
                    models.File.query.with_entities(
                        sqlalchemy.func.sum(models.File.size_original).label("sizeSum")
                    )
                    .filter(models.File.project_id == current_project.id)
                    .first()
                )

                current_project.size = tot_file_size.sizeSum
                current_project.date_updated = timestamp()
                db.session.commit()
            except sqlalchemy.exc.SQLAlchemyError as err:
                error = str(err)
                db.session.rollback()
                current_try += 1
            else:
                updated = True
                break

        return flask.jsonify({"updated": updated, "error": error, "tries": current_try})
