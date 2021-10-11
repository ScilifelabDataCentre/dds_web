"""Project module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import functools

# Installed
import flask_restful
import flask
import sqlalchemy
from cryptography.hazmat.primitives.kdf import scrypt
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_decrypt as decrypt
from cryptography.hazmat import backends
import os


# Own modules
import dds_web.utils
from dds_web import auth, db
from dds_web.database import models
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.db_connector import DBConnector
from dds_web.api.errors import (
    MissingProjectIDError,
    DatabaseError,
    NoSuchProjectError,
    AccessDeniedError,
    EmptyProjectException,
    DeletionError,
    BucketNotFoundError,
    PublicKeyNotFoundError,
    DDSArgumentError,
)
from dds_web.api import marshmallows
from dds_web.crypt import key_gen

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class GetPublic(flask_restful.Resource):
    """Gets the public key beloning to the current project."""

    @auth.login_required  # All roles can access this for different reasons
    def get(self):
        """Get public key from database."""

        public_key = marshmallows.PublicKeySchema().load(flask.request.args)

        flask.current_app.logger.info("Returning public key...")
        return flask.jsonify({"public": public_key})


class GetPrivate(flask_restful.Resource):
    """Gets the private key belonging to the current project."""

    @auth.login_required
    def get(self):
        """Get private key from database"""

        private_key_encrypted, nonce, salt = marshmallows.PrivateKeySchema().load(
            flask.request.args
        )

        flask.current_app.logger.debug(f"{private_key_encrypted}, {nonce}, {salt}")
        # return
        # TODO (ina): Change handling of private key -- not secure

        app_secret = flask.current_app.config.get("SECRET_KEY")
        passphrase = app_secret.encode("utf-8")

        kdf = scrypt.Scrypt(
            salt=salt,
            length=32,
            n=2 ** 14,
            r=8,
            p=1,
            backend=backends.default_backend(),
        )

        privkey_decryption_key = kdf.derive(passphrase)
        try:
            private_key = decrypt(
                ciphertext=private_key_encrypted, aad=None, nonce=nonce, key=privkey_decryption_key
            )
        except Exception as err:
            flask.current_app.logger.exception(err)
            return flask.make_response(str(err), 500)

        flask.current_app.logger.info("Returning private key...")
        return flask.jsonify({"private": private_key.hex().upper()})


class UserProjects(flask_restful.Resource):
    """Gets all projects registered to a specific user."""

    @auth.login_required
    def get(self):
        """Get info regarding all projects which user is involved in."""

        current_user = auth.current_user()

        # TODO: Return different things depending on if unit or not
        all_projects = list()

        # Total number of GB hours and cost saved in the db for the specific unit
        total_gbhours_db = 0.0
        total_cost_db = 0.0
        total_size = 0

        # Unit users can get usage info
        return_usage = flask.request.args.get("usage") == "True" and current_user.role in [
            "Unit Personnel",
            "Unit Admin",
        ]

        try:

            # Get info for all projects
            for proj in current_user.projects:

                flask.current_app.logger.info(proj)
                project_info = {
                    "Project ID": proj.public_id,
                    "Title": proj.title,
                    "PI": proj.pi,
                    "Status": proj.status,
                    "Last updated": proj.date_updated if proj.date_updated else proj.date_created,
                    "Size": dds_web.utils.format_byte_size(proj.size),
                }

                # Get proj size and update total size
                proj_size = sum([f.size_stored for f in proj.files])
                total_size += proj_size
                project_info["Size"] = dds_web.utils.format_byte_size(proj_size)

                # Get project usage if chosen and allowed
                if return_usage:
                    proj_gbhours, proj_cost = DBConnector().project_usage(proj)
                    total_gbhours_db += proj_gbhours
                    total_cost_db += proj_cost

                    project_info.update({"GBHours": str(proj_gbhours), "Cost": str(proj_cost)})

                all_projects.append(project_info)
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError

        return_info = {
            "project_info": all_projects,
            "total_usage": {
                "gbhours": str(round(total_gbhours_db, 2)) if total_gbhours_db > 1.0 else str(0),
                "cost": f"{round(total_cost_db, 2)} kr" if total_cost_db > 1.0 else f"0 kr",
            },
            "total_size": dds_web.utils.format_byte_size(total_size),
        }

        return flask.jsonify(return_info)


class RemoveContents(flask_restful.Resource):
    """Removes all project contents."""

    @auth.login_required
    def delete(self):
        """Removes all project contents."""

        project = marshmallows.DeletePermissionsRequiredSchema().load(flask.request.args)

        # Delete files
        removed = False
        with DBConnector(project=project) as dbconn:
            try:
                removed = dbconn.delete_all()
            except (DatabaseError, EmptyProjectException):
                raise

            # Return error if contents not deleted from db
            if not removed:
                raise DeletionError(
                    message="No project contents deleted.",
                    username=current_user.username,
                    project=project.public_id,
                )

            # Delete from bucket
            try:
                with ApiS3Connector() as s3conn:
                    removed = s3conn.remove_all()

                    # Return error if contents not deleted from s3 bucket
                    if not removed:
                        db.session.rollback()
                        raise DeletionError(
                            message="Deleting project contents failed.",
                            username=current_user.username,
                            project=project.public_id,
                        )

                    # Commit changes to db
                    db.session.commit()
            except sqlalchemy.exc.SQLAlchemyError as err:
                raise DatabaseError(message=str(err))
            except (DeletionError, BucketNotFoundError):
                raise

        return flask.jsonify({"removed": removed})


class UpdateProjectSize(flask_restful.Resource):
    @auth.login_required
    def put(self):
        """Update the project size and updated time stamp."""

        project = marshmallows.UploadPermissionsRequiredSchema().load(flask.request.args)

        updated, error = (False, "")
        current_try, max_tries = (1, 5)
        while current_try < max_tries:
            try:
                tot_file_size = (
                    models.File.query.with_entities(
                        sqlalchemy.func.sum(models.File.size_original).label("sizeSum")
                    )
                    .filter(models.File.project_id == project.id)
                    .first()
                )

                project.size = tot_file_size.sizeSum
                project.date_updated = dds_web.utils.current_time()

                db.session.commit()
            except sqlalchemy.exc.SQLAlchemyError as err:
                flask.current_app.logger.exception(err)
                db.session.rollback()
                current_try += 1
            else:
                flask.current_app.logger.debug("Updated project size!")
                updated = True
                break

        return flask.jsonify({"updated": updated, "error": error, "tries": current_try})


class CreateProject(flask_restful.Resource):
    @auth.login_required(role="Unit Personnel")
    def post(self):
        """Create a new project"""

        if flask.request.is_json:
            try:
                p_info = flask.request.json
            except:
                raise DDSArgumentError(message="Error: Malformed data provided")
        else:
            raise DDSArgumentError(message="Error: Malformed data provided")

        if "title" not in p_info or "description" not in p_info:
            raise DDSArgumentError(
                message="Error: Title/description missing when creating a project"
            )
        cur_user = auth.current_user()
        # Add check for user permissions

        created_time = dds_web.utils.current_time()

        try:
            # lock Unit row
            unit_row = (
                db.session.query(models.Unit)
                .filter_by(id=cur_user.unit_id)
                .with_for_update()
                .one_or_none()
            )

            if not unit_row:
                raise AccessDeniedError(message=f"Error: Your user is not associated to a unit.")

            unit_row.counter = unit_row.counter + 1 if unit_row.counter else 1
            public_id = "{}{:03d}".format(unit_row.internal_ref, unit_row.counter)

            project_info = {
                "public_id": public_id,
                "title": p_info["title"],
                "unit_id": unit_row,
                "created_by": cur_user.username,
                "date_created": created_time,
                "date_updated": created_time,
                "status": "Ongoing",  # ?
                "description": p_info["description"],
                "pi": p_info.get("pi", ""),  # Not a foreign key, only a name
                "size": 0,
                "bucket": self.__create_bucket_name(public_id, created_time),
            }
            pkg = key_gen.ProjectKeys(project_info["public_id"])
            project_info.update(pkg.key_dict())

            new_project = models.Project(**project_info)
            unit_row.projects.append(new_project)
            cur_user.created_projects.append(new_project)
            db.session.commit()

        except (sqlalchemy.exc.SQLAlchemyError, TypeError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise DatabaseError(message="Server Error: Project was not created")

        else:
            flask.current_app.logger.debug(
                f"Project {public_id} created by user {cur_user.username}."
            )
            return flask.jsonify(
                {
                    "status": 200,
                    "message": "Added new project '{}'".format(new_project.title),
                    "project_id": new_project.public_id,
                }
            )

    def __create_bucket_name(self, public_id, created_time):
        """Create a bucket name for the given project"""
        return "{pid}-{tstamp}-{rstring}".format(
            pid=public_id.lower(),
            tstamp=dds_web.utils.timestamp(dts=created_time, ts_format="%y%m%d%H%M%S%f"),
            rstring=os.urandom(4).hex(),
        )
