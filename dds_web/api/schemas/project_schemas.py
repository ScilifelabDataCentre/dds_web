"""Project related marshmallow schemas."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import os

# Installed
import flask
import marshmallow
import sqlalchemy

# Own modules
from dds_web import errors as ddserr
from dds_web import auth, db
from dds_web.database import models
from dds_web.api import api_s3_connector
from dds_web.api.schemas import sqlalchemyautoschemas
from dds_web.api.schemas import custom_fields
import dds_web.utils
from dds_web.crypt import key_gen
import cryptography
from dds_web.security import project_keys

####################################################################################################
# VALIDATORS ########################################################################## VALIDATORS #
####################################################################################################


def verify_project_exists(spec_proj):
    """Check that project exists."""

    try:
        project = models.Project.query.filter(
            models.Project.public_id == sqlalchemy.func.binary(spec_proj)
        ).one_or_none()
    except sqlalchemy.exc.SQLAlchemyError as sqlerr:
        raise

    if not project:
        flask.current_app.logger.warning("No such project!!")
        raise ddserr.NoSuchProjectError(project=spec_proj)

    return project


def verify_project_access(project):
    """Check users access to project."""

    if project not in auth.current_user().projects:
        raise ddserr.AccessDeniedError(
            message="Project access denied.",
            username=auth.current_user().username,
            project=project.public_id,
        )

    return project


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

    @marshmallow.pre_load
    def generate_required_fields(self, data, **kwargs):
        """Generate all required fields for creating a project."""
        if not data:
            raise ddserr.DDSArgumentError(
                "No project information found when attempting to create project."
            )

        data["date_created"] = dds_web.utils.current_time()

        return data

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def validate_all_fields(self, data, **kwargs):
        """Validate that all fields are present."""
        if not all(
            field in data
            for field in [
                "title",
                "date_created",
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
                models.Unit.query.filter_by(id=auth.current_user().unit_id)
                .with_for_update()
                .one_or_none()
            )
            if not unit_row:
                raise ddserr.AccessDeniedError(
                    message=f"Error: Your user is not associated to a unit."
                )

            unit_row.counter = unit_row.counter + 1 if unit_row.counter else 1
            data["public_id"] = "{}{:03d}".format(unit_row.internal_ref, unit_row.counter)

            # Generate bucket name
            data["bucket"] = self.generate_bucketname(
                public_id=data["public_id"], created_time=data["date_created"]
            )

            # NOTE: TEMPORARY
            # Generate keys and add to project
            # data.update(**key_gen.ProjectKeys(data["public_id"]).key_dict())
            # ----

            # Create project
            current_user = auth.current_user()
            project_key_pair = project_keys.generate_project_key_pair(user=current_user)
            flask.current_app.logger.debug(f"project_key_pair: {project_key_pair}")

            new_project = models.Project(
                **{
                    **data,
                    "unit_id": current_user.unit.id,
                    "created_by": current_user.username,
                    "public_key": project_key_pair["public_key"],
                }
            )
            new_project.project_statuses.append(
                models.ProjectStatuses(
                    **{
                        "status": "In Progress",
                        "date_created": data["date_created"],
                    }
                )
            )
            # Generate keys
            # NOTE: TEMPORARY:
            # key=b"temp" * 8 is only a temporary KEK until we have the actual KEK
            # temporary_kek = project_keys.derive_key(user=current_user, password="password")
            # flask.current_app.logger.debug(f"temporary_kek: {temporary_kek} ({len(temporary_kek)})")
            #  b'\xda\xcd\x81\x0f\x0c\\\x03\xb4\xad\x0f\x0b\x85\xe6ib@\x03\x19\x8axD\x99aC\xa0\x88xZ\x13\x84\xe5{' (32)

            # aesgcm = cryptography.hazmat.primitives.ciphers.aead.AESGCM(key=temporary_kek)
            nonce = project_key_pair["encrypted_private_key"]["nonce"]
            project_private_key = project_key_pair["encrypted_private_key"]["encrypted_key"]
            flask.current_app.logger.debug(
                f"project_private_key before encrypted by temp kek: {project_private_key}"
            )
            # b"\xe5\x0c\x1f\xa0\xebj\x04\x00\x93\xadV\xfc\xbf9J\xe1J\xc4v`V!d^'/\x8d\xd2/\xe8\xc7\xa5\x99a\xa7\x89\x0e9Z\x12N\xc0\x9f8\xecS\xe6o"
            aad = None
            # ----

            # Add new project keys to table.
            new_project_key = models.ProjectKeys(
                # key=aesgcm.encrypt(nonce=nonce, data=project_private_key, associated_data=aad),
                key=project_private_key,
                nonce=nonce,
            )
            flask.current_app.logger.debug(
                f"project_private_key after encrypted by temp kek: {new_project_key.key}"
            )

            # Save
            auth.current_user().project_keys.append(new_project_key)
            new_project.project_keys.append(new_project_key)
            db.session.add(new_project)
            db.session.commit()
        except (sqlalchemy.exc.SQLAlchemyError, TypeError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise ddserr.DatabaseError(message="Server Error: Project was not created")
        except (
            marshmallow.ValidationError,
            ddserr.DDSArgumentError,
            ddserr.AccessDeniedError,
        ) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise

        return new_project


class ProjectRequiredSchema(marshmallow.Schema):
    """Schema for verifying an existing project in args and database."""

    project = marshmallow.fields.String(required=True)

    class Meta:
        unknown = marshmallow.EXCLUDE  # TODO: Change to RAISE

    @marshmallow.validates("project")
    def validate_project(self, value):
        """Validate existing project and user access to it."""

        project = verify_project_exists(spec_proj=value)
        verify_project_access(project=project)

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def get_project_object(self, data, **kwargs):
        """Set project row in data for access by validators."""

        data["project_row"] = verify_project_exists(spec_proj=data.get("project"))

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Return project object."""

        return data.get("project_row")


class ProjectContentSchema(ProjectRequiredSchema):
    """ """

    requested_items = marshmallow.fields.List(marshmallow.fields.String, required=False)
    url = marshmallow.fields.Boolean(required=False, default=False)
    get_all = marshmallow.fields.Boolean(required=False, default=False)

    def find_contents(self, project, contents):

        # All contents
        all_contents_query = models.File.query.filter(
            models.File.project_id == sqlalchemy.func.binary(project.id)
        )

        # Get all files
        files = all_contents_query.filter(models.File.name.in_(contents)).all()

        # Get not found paths - may be folders
        new_paths = set(contents).difference(x.name for x in files)

        # Get all folder contents
        folder_contents = {
            x: all_contents_query.filter(models.File.subpath.like(f"{x.rstrip(os.sep)}%")).all()
            for x in new_paths
        }

        # Not found
        not_found = {x: folder_contents.pop(x) for x, y in list(folder_contents.items()) if not y}

        return files, folder_contents, not_found

    @marshmallow.post_dump
    def return_items(self, data, **kwargs):
        """Return project contents as serialized."""

        # Fields
        requested_items = data.get("requested_items")
        url = data.get("url")
        get_all = data.get("get_all")

        # Check if project has contents
        project_row = verify_project_exists(spec_proj=data.get("project"))
        if not project_row.files:
            raise ddserr.EmptyProjectException

        # Check if specific files have been requested or if requested all contents
        files, folder_contents, not_found = (None, None, None)
        if requested_items:
            files, folder_contents, not_found = self.find_contents(
                project=project_row, contents=requested_items
            )
        elif get_all:
            files = project_row.files
        else:
            raise ddserr.DDSArgumentError(message="No items were requested.")

        # Items to return
        found_files = {}
        found_folder_contents = {}
        not_found = {}

        # Use file schema to get file info automatically
        fileschema = sqlalchemyautoschemas.FileSchema(
            many=False,
            only=(
                "name_in_bucket",
                "subpath",
                "size_original",
                "size_stored",
                "salt",
                "public_key",
                "checksum",
                "compressed",
            ),
        )

        # Connect to s3
        with api_s3_connector.ApiS3Connector(project=project_row) as s3:
            # Get the info and signed urls for all files
            found_files.update(
                {
                    x.name: {
                        **fileschema.dump(x),
                        "url": s3.generate_get_url(key=x.name_in_bucket) if url else None,
                    }
                    for x in files
                }
            )

            if folder_contents:
                # Get all info and signed urls for all folder contents found in the bucket
                for x, y in folder_contents.items():
                    if x not in found_folder_contents:
                        found_folder_contents[x] = {}

                    found_folder_contents[x].update(
                        {
                            z.name: {
                                **fileschema.dump(z),
                                "url": s3.generate_get_url(key=z.name_in_bucket) if url else None,
                            }
                            for z in y
                        }
                    )

        return found_files, found_folder_contents, not_found
