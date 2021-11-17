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
import marshmallow


# Own modules
import dds_web.utils
from dds_web import auth, db
from dds_web.database import models
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.db_connector import DBConnector
from dds_web.api.errors import (
    DDSArgumentError,
    DatabaseError,
    AccessDeniedError,
    EmptyProjectException,
    DeletionError,
    BucketNotFoundError,
    KeyNotFoundError,
)
from dds_web.crypt import key_gen
from dds_web.api.user import AddUser
from dds_web.api.schemas import custom_fields
from dds_web.api.schemas import project_schemas
from dds_web.api.schemas import user_schemas

####################################################################################################
# SCHEMAS ################################################################################ SCHEMAS #
####################################################################################################


class CreateProjectSchema(marshmallow.Schema):
    """Schema for creating a project."""

    class Meta:
        unknown = marshmallow.EXCLUDE

    title = marshmallow.fields.String(required=True, validate=marshmallow.validate.Length(min=1))
    description = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(min=1)
    )
    pi = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(min=1, max=255)
    )
    is_sensitive = marshmallow.fields.Boolean(required=False)
    date_created = custom_fields.MyDateTimeField(required=False)

    # Only "In Progress" allowed when creating the project
    status = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Equal("In Progress")
    )

    @marshmallow.pre_load
    def generate_required_fields(self, data, **kwargs):
        """Generate all required fields for creating a project."""
        if not data:
            raise DDSArgumentError(
                "No project information found when attempting to create project."
            )

        data["date_created"] = dds_web.utils.current_time()
        data["status"] = "In Progress"

        return data

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def validate_all_fields(self, data, **kwargs):
        """Validate that all fields are present."""
        if not all(
            field in data
            for field in [
                "title",
                "date_created",
                "status",
                "description",
                "pi",
            ]
        ):
            raise marshmallow.ValidationError("Missing fields!")

    def generate_bucketname(self, public_id, created_time):
        """Create bucket name for the given project."""
        return "{pid}-{tstamp}-{rstring}".format(
            pid=public_id.lower(),
            tstamp=dds_web.utils.timestamp(dts=created_time, ts_format="%y%m%d%H%M%S%f"),
            rstring=os.urandom(4).hex(),
        )

    @marshmallow.post_load
    def create_project(self, data, **kwargs):
        """Create project row in db."""

        try:
            # Lock db, get unit row and update counter
            unit_row = (
                db.session.query(models.Unit)
                .filter_by(id=auth.current_user().unit_id)
                .with_for_update()
                .one_or_none()
            )
            if not unit_row:
                raise AccessDeniedError(message=f"Error: Your user is not associated to a unit.")

            unit_row.counter = unit_row.counter + 1 if unit_row.counter else 1
            data["public_id"] = "{}{:03d}".format(unit_row.internal_ref, unit_row.counter)

            # Generate bucket name
            data["bucket"] = self.generate_bucketname(
                public_id=data["public_id"], created_time=data["date_created"]
            )

            # Generate keys
            data.update(**key_gen.ProjectKeys(data["public_id"]).key_dict())

            # Create project
            current_user = auth.current_user()
            new_project = models.Project(
                **{**data, "unit_id": current_user.unit.id, "created_by": current_user.username}
            )

            # Save
            db.session.add(new_project)
            db.session.commit()
        except (sqlalchemy.exc.SQLAlchemyError, TypeError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise DatabaseError(message="Server Error: Project was not created")
        except (marshmallow.ValidationError, DDSArgumentError, AccessDeniedError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise

        return new_project


####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class GetPublic(flask_restful.Resource):
    """Gets the public key beloning to the current project."""

    @auth.login_required
    def get(self):
        """Get public key from database."""

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        flask.current_app.logger.debug("Getting the public key.")

        if not project.public_key:
            raise KeyNotFoundError(project=project.public_id)

        return flask.jsonify({"public": project.public_key})


class GetPrivate(flask_restful.Resource):
    """Gets the private key belonging to the current project."""

    @auth.login_required
    def get(self):
        """Get private key from database"""

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

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
            raise KeyNotFoundError

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
        total_bhours_db = 0.0
        total_cost_db = 0.0
        total_size = 0

        usage = flask.request.args.get("usage") == "True" and current_user.role in [
            "Super Admin",
            "Unit Admin",
            "Unit Personnel",
        ]

        # Get info for all projects
        for p in current_user.projects:
            project_info = {
                "Project ID": p.public_id,
                "Title": p.title,
                "PI": p.pi,
                "Status": p.status,
                "Last updated": p.date_updated if p.date_updated else p.date_created,
                "Size": p.size,
            }

            # Get proj size and update total size
            proj_size = p.size
            total_size += proj_size
            project_info["Size"] = proj_size

            if usage:
                proj_bhours, proj_cost = DBConnector().project_usage(p)
                total_bhours_db += proj_bhours
                total_cost_db += proj_cost
                # return ByteHours
                project_info.update({"Usage": proj_bhours, "Cost": proj_cost})

            all_projects.append(project_info)

        return_info = {
            "project_info": all_projects,
            "total_usage": {
                # return ByteHours
                "usage": total_bhours_db,
                "cost": total_cost_db,
            },
            "total_size": total_size,
        }

        return flask.jsonify(return_info)


class RemoveContents(flask_restful.Resource):
    """Removes all project contents."""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    def delete(self):
        """Removes all project contents."""

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

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


class CreateProject(flask_restful.Resource):
    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    def post(self):
        """Create a new project"""

        p_info = flask.request.json

        new_project = CreateProjectSchema().load(p_info)

        if not new_project:
            raise DDSArgumentError("Failed to create project.")

        flask.current_app.logger.debug(
            f"Project {new_project.public_id} created by user {auth.current_user().username}."
        )
        user_addition_statuses = []
        if "users_to_add" in p_info:
            for user in p_info["users_to_add"]:
                existing_user = user_schemas.UserSchema().load(user)
                if not existing_user:
                    # Send invite if the user doesn't exist
                    invite_user_result = AddUser.invite_user(
                        {
                            "email": user.get("email"),
                            "role": user.get("role"),
                        }
                    )
                    if invite_user_result["status"] == 200:
                        invite_msg = f"Invitation sent to {user['email']}. The user should have a valid account to be added to a project"
                    else:
                        invite_msg = invite_user_result["message"]
                    user_addition_statuses.append(invite_msg)
                else:
                    # If it is an existing user, add them to project.
                    addition_status = ""
                    try:
                        add_user_result = AddUser.add_user_to_project(
                            existing_user=existing_user,
                            project=new_project.public_id,
                            role=user.get("role"),
                        )
                    except DatabaseError as err:
                        addition_status = f"Error for {user['email']}: {err.description}"
                    else:
                        addition_status = add_user_result["message"]
                    user_addition_statuses.append(addition_status)

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

        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

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
