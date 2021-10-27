"""Project module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library

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
    DDSArgumentError,
    KeyNotFoundError,
)
from dds_web.crypt import key_gen
from dds_web.api import marshmallows
from dds_web.api.user import AddUser

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class GetPublic(flask_restful.Resource):
    """Gets the public key beloning to the current project."""

    @auth.login_required
    def get(self):
        """Get public key from database."""

        project = marshmallows.ProjectRequiredSchema().load(flask.request.args)

        flask.current_app.logger.debug("Getting the public key.")

        if not project.public_key:
            raise KeyNotFoundError(project=project.public_id)

        return flask.jsonify({"public": project.public_key})


class GetPrivate(flask_restful.Resource):
    """Gets the private key belonging to the current project."""

    @auth.login_required
    def get(self):
        """Get private key from database"""

        project = marshmallows.ProjectRequiredSchema().load(flask.request.args)

        # TODO (ina): Change handling of private key -- not secure
        flask.current_app.logger.debug("Getting the private key.")

        app_secret = flask.current_app.config.get("SECRET_KEY")
        passphrase = app_secret.encode("utf-8")

        enc_key = bytes.fromhex(project.private_key)
        nonce = bytes.fromhex(project.privkey_nonce)
        salt = bytes.fromhex(project.privkey_salt)

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
            flask.current_app.logger.exception(err)
            return flask.make_response(str(err), 500)

        return flask.jsonify({"private": decrypted_key.hex().upper()})


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

        usage = flask.request.args.get("usage") == "True" and current_user.role == "unit"

        # Get info for all projects
        for p in current_user.projects:
            project_info = {
                "Project ID": p.public_id,
                "Title": p.title,
                "PI": p.pi,
                "Status": p.status,
                "Last updated": p.date_updated if p.date_updated else p.date_created,
                "Size": dds_web.utils.format_byte_size(p.size),
            }

            # Get proj size and update total size
            proj_size = sum([f.size_stored for f in p.files])
            total_size += proj_size
            project_info["Size"] = dds_web.utils.format_byte_size(proj_size)

            if usage:
                proj_gbhours, proj_cost = DBConnector().project_usage(p)
                total_gbhours_db += proj_gbhours
                total_cost_db += proj_cost

                project_info.update({"GBHours": str(proj_gbhours), "Cost": str(proj_cost)})

            all_projects.append(project_info)

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

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    def delete(self):
        """Removes all project contents."""

        project = marshmallows.ProjectRequiredSchema().load(flask.request.args)

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
                with ApiS3Connector(project=project) as s3conn:
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
    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    def put(self):
        """Update the project size and updated time stamp."""

        project = marshmallows.ProjectRequiredSchema().load(flask.request.args)

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
    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    def post(self):
        """Create a new project"""

        p_info = flask.request.json
        new_project = marshmallows.CreateProjectSchema().load(p_info)

        try:
            db.session.add(new_project)
            db.session.commit()

        except (sqlalchemy.exc.SQLAlchemyError, TypeError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise DatabaseError(message="Server Error: Project was not created")

        else:
            flask.current_app.logger.debug(
                f"Project {new_project.public_id} created by user {auth.current_user().username}."
            )
            user_addition_statuses = []
            if "users_to_add" in p_info:
                for user in p_info["users_to_add"]:
                    owner = user.pop("owner", False)

                    existing_user = marshmallows.UserSchema().load(user)
                    if not existing_user:
                        # Send invite if the user doesn't exist
                        invite_user_result = AddUser.invite_user(
                            {
                                "email": user.get("email"),
                                "role": "Project Owner" if owner else "Researcher",
                            }
                        )
                        if invite_user_result["status"] == 200:
                            invite_msg = f"Invitation sent to {user['email']}. The user should have a valid account to be added to a project"
                        else:
                            invite_msg = invite_user_result["message"]
                        user_addition_statuses.append(invite_msg)
                    else:
                        # If it is an existing user, add them to project.
                        add_user_result = AddUser.add_user_to_project(
                            existing_user=existing_user, project=new_project.public_id, owner=owner
                        )
                        user_addition_statuses.append(add_user_result["message"])

            return flask.jsonify(
                {
                    "status": 200,
                    "message": "Added new project '{}'".format(new_project.title),
                    "project_id": new_project.public_id,
                    "user_addition_statuses": user_addition_statuses,
                }
            )


class ProjectUsers(flask_restful.Resource):
    """Get all users in a specific project."""

    @auth.login_required
    def get(self):

        project = marshmallows.ProjectRequiredSchema().load(flask.request.args)

        # Get info on research users
        research_users = list()

        for user in project.researchusers:
            user_info = {
                "User Name": user.user_id,
                "Primary email": "",
            }
            for user_email in user.researchuser.emails:
                if user_email.primary:
                    user_info["Primary email"] = user_email.email
            research_users.append(user_info)

        return flask.jsonify({"research_users": research_users})
