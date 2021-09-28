"""Project module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Installed
import flask_restful
import flask
import sqlalchemy
from cryptography.hazmat.primitives.kdf import scrypt
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_decrypt as decrypt
from cryptography.hazmat import backends


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
)

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


def verify(current_user, project_public_id, access_method):
    """Checks the user access to the given project with the given method."""

    if not project_public_id:
        raise MissingProjectIDError

    flask.current_app.logger.debug(
        f"Verifying access to project {project_public_id} by user {current_user.username}."
    )
    try:
        project = models.Project.query.filter(models.Project.public_id == project_public_id).first()
    except sqlalchemy.exc.SQLAlchemyError as sqlerr:
        raise DatabaseError(
            message=str(sqlerr), username=current_user.username, project=project_public_id
        )

    if not project:
        raise NoSuchProjectError(username=current_user.username, project=project_public_id)

    if project not in current_user.projects:
        raise AccessDeniedError(
            message="Project access denied.",
            username=current_user.username,
            project=project_public_id,
        )

    has_one_of_the_permissions = False
    for method in access_method:
        if method in ["put", "rm"]:
            if current_user.role in ["unit", "admin"]:
                has_one_of_the_permissions = True
        else:  # get or ls
            has_one_of_the_permissions = True

    if not has_one_of_the_permissions:
        raise AccessDeniedError(
            message="User does not have necessary permission(s) in the specified project.",
            username=current_user.username,
            project=project_public_id,
        )

    flask.current_app.logger.debug(
        f"Access to project {project_public_id} is granted for user {current_user.username}."
    )
    return project


class GetPublic(flask_restful.Resource):
    """Gets the public key beloning to the current project."""

    @auth.login_required
    def get(self):
        """Get public key from database."""

        args = flask.request.args

        project = verify(
            current_user=auth.current_user(),
            project_public_id=args.get("project"),
            access_method=["get", "put"],
        )

        flask.current_app.logger.debug("Getting the public key.")

        if not project.public_key:
            raise PublicKeyNotFoundError(project=project.public_id)

        return flask.jsonify({"public": project.public_key})


class GetPrivate(flask_restful.Resource):
    """Gets the private key belonging to the current project."""

    @auth.login_required
    def get(self):
        """Get private key from database"""

        args = flask.request.args

        project = verify(
            current_user=auth.current_user(),
            project_public_id=args.get("project"),
            access_method=["get"],
        )

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
                "Last updated": dds_web.utils.timestamp(
                    datetime_string=p.date_updated if p.date_updated else p.date_created
                ),
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

    @auth.login_required
    def delete(self):
        """Removes all project contents."""

        args = flask.request.args
        current_user = auth.current_user()
        project = verify(
            current_user=current_user, project_public_id=args.get("project"), access_method=["rm"]
        )

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

        args = flask.request.args

        project = verify(
            current_user=auth.current_user(),
            project_public_id=args.get("project"),
            access_method=["put"],
        )

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
                project.date_updated = dds_web.utils.timestamp()
                db.session.commit()
            except sqlalchemy.exc.SQLAlchemyError as err:
                error = str(err)
                db.session.rollback()
                current_try += 1
            else:
                updated = True
                break

        return flask.jsonify({"updated": updated, "error": error, "tries": current_try})
