"""Marshmallow schemas used by the DDS"""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import os

# Installed
import flask
import marshmallow
import sqlalchemy
import immutabledict

# Own modules
from dds_web import db
from dds_web.api import errors as ddserr
from dds_web import auth
import dds_web.security.auth
from dds_web.database import models
from dds_web import utils

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


def email_in_db(email):
    """Check if the email is in the Email table."""

    if models.Email.query.filter_by(email=email).first():
        return True

    return False


def username_in_db(username):
    """Check if username is in the User table."""

    if models.User.query.filter_by(username=username).first():
        return True

    return False


####################################################################################################
# SCHEMAS ################################################################################ SCHEMAS #
####################################################################################################

# Project related ---------------------------------------------------------------- Project related #


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


# User related ---------------------------------------------------------------------- User related #


class UserSchema(marshmallow.Schema):
    """Schema for User class."""

    email = marshmallow.fields.Email(required=True)

    class Meta:
        unknown = marshmallow.EXCLUDE

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def validate_email_and_user(self, data, **kwargs):
        """Check that the email and connected user exists in the database."""
        flask.current_app.logger.debug("Validating email and user...")
        email_row = models.Email.query.filter_by(email=data.get("email")).first()
        if not email_row:
            raise ddserr.NoSuchUserError

        data["user"] = email_row.user

    @marshmallow.post_load
    def return_user(self, data, **kwargs):
        """Return the user."""

        return data.get("user")


class AddUserSchema(ProjectRequiredSchema):
    """Add existing user to project"""

    # TODO


class InviteUserSchema(marshmallow.Schema):
    """Schema for AddUser endpoint"""

    email = marshmallow.fields.Email(required=True)  # Validator below
    role = marshmallow.fields.String(
        required=True,
        validate=marshmallow.validate.OneOf(
            choices=["Super Admin", "Unit Admin", "Unit Personnel", "Project Owner", "Researcher"],
        ),
    )

    @marshmallow.validates("email")
    def validate_email(self, value):
        """Check that email is not used by anyone in db."""

        if models.Invite.query.filter_by(email=value).first():
            raise ddserr.InviteError(message=f"Email '{value}' already has a pending invitation.")
        elif email_in_db(email=value):
            raise ddserr.InviteError(
                message=f"The email '{value}' is already registered to an existing user."
            )

    @marshmallow.validates("role")
    def validate_role(self, attempted_invite_role):
        """Validate current users permission to invite specified role."""

        curr_user_role = auth.current_user().role
        if curr_user_role == "Unit Admin":
            if attempted_invite_role == "Super Admin":
                raise ddserr.AccessDeniedError
        elif curr_user_role == "Unit Personnel":
            if attempted_invite_role in ["Super Admin", "Unit Admin"]:
                raise ddserr.AccessDeniedError
        elif curr_user_role == "Researcher":
            # research users can only invite in certain projects if they are set as the owner
            # TODO: Add required project field for researchers to be able to invite (if
            raise ddserr.AccessDeniedError(
                message=(
                    "Research users cannot invite at this time. "
                    "Project owner invite config will be fixed."
                )
            )

    @marshmallow.post_load
    def make_invite(self, data, **kwargs):
        """Deserialize to an Invite object"""

        if data.get("role") == "Super Admin":
            # TODO: here the unit needs to be specified
            raise marshmallow.ValidationError("currently not creating invites for superadmins")

        # Create invite
        new_invite = models.Invite(**{"email": data.get("email"), "role": data.get("role")})

        # Append invite to unit if applicable
        if new_invite.role in ["Unit Admin", "Unit Personnel"]:
            auth.current_user().unit.invites.append(new_invite)
        else:
            db.session.add(new_invite)

        db.session.commit()

        return new_invite


class NewUserSchema(marshmallow.Schema):
    """Schema for NewUser endpoint"""

    # TODO: Look through and match to db
    username = marshmallow.fields.String(
        required=True,
        validate=marshmallow.validate.Regexp(
            regex="^[a-zA-Z0-9_]{6,25}$",
            # username must be between 6-25 characters long and contain a-z, A-Z, 0-9
        ),
    )
    password = marshmallow.fields.String(
        required=True,
        validate=marshmallow.validate.Regexp(
            regex="^(?=[^a-z\n]*[a-z])(?=[^A-Z\n]*[A-Z])(?=[^\d\n]*\d)^[\S]{10,64}$",
            # Password must contain one or more uppercase, lowercase and digit characters.
            # It may contain special characters (not enforced), as they might be hard to type depending on keyboard layout (e.g. on smartphones)
            # Length of the password must be between 10 and 64 characers
        ),
    )
    email = marshmallow.fields.Email(required=True, validate=marshmallow.validate.Email())
    name = marshmallow.fields.String(required=True, validate=marshmallow.validate.Length(max=255))

    class Meta:
        """Exclude unknown fields e.g. csrf etc that are passed with form"""

        unknown = marshmallow.EXCLUDE

    @marshmallow.validates("username")
    def verify_username(self, value):
        """Verify that the username is not used in the system."""

        if username_in_db(username=value):
            raise marshmallow.ValidationError(
                message=(
                    f"The username '{value}' is already taken by another user. "
                    "Try something else."
                )
            )

    @marshmallow.validates("email")
    def verify_new_email(self, value):
        """Verify that the email is not used in the system already."""

        if email_in_db(email=value):
            raise marshmallow.ValidationError(
                message=f"The email '{value}' is already registered to an existing user."
            )

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def verify_and_get_invite(self, data, **kwargs):
        """Verifies that the email is in the invite table and in that case saves the invite info."""

        invite = models.Invite.query.filter(
            models.Invite.email == sqlalchemy.func.binary(data.get("email"))
        ).one_or_none()
        if not invite:
            raise ddserr.InviteError

        data["invite"] = invite

    @marshmallow.post_load
    def make_user(self, data, **kwargs):
        """Deserialize to an User object"""

        # Hash password
        password = dds_web.security.auth.gen_argon2hash(password=data.get("password"))

        common_user_fields = {
            "username": data.get("username"),
            "password": password,
            "name": data.get("name"),
        }

        # Create new user
        invite = data.get("invite")
        if invite.role == "Researcher":
            new_user = models.ResearchUser(**common_user_fields)
            # Currently no project associations
        elif invite.role in ["Unit Admin", "Unit Personnel"]:
            new_user = models.UnitUser(**common_user_fields)

            new_user.is_admin = invite.role == "Unit Admin"

            invite.unit.users.append(new_user)
        elif new_user_role == "Super Admin":
            new_user = models.SuperAdmin(**common_user_fields)

        # Create new email and append to user relationship
        new_email = models.Email(email=data.get("email"), primary=True)
        new_user.emails.append(new_email)

        db.session.add(new_user)

        # Delete old invite
        db.session.delete(invite)

        # Save and return
        db.session.commit()

        return new_user


# File related ---------------------------------------------------------------------- File related #


class NewFileSchema(ProjectRequiredSchema):
    """Validates and creates a new file object."""

    # Length minimum 1 required, required=True accepts empty string
    name = marshmallow.fields.String(required=True, validate=marshmallow.validate.Length(min=1))
    name_in_bucket = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(min=1)
    )
    subpath = marshmallow.fields.String(required=True, validate=marshmallow.validate.Length(min=1))
    size = marshmallow.fields.Integer(required=True)  # Accepts BigInt
    size_processed = marshmallow.fields.Integer(required=True)  # Accepts BigInt
    compressed = marshmallow.fields.Boolean(required=True)  # Accepts all truthy
    public_key = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(equal=64)
    )
    salt = marshmallow.fields.String(required=True, validate=marshmallow.validate.Length(equal=32))
    checksum = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(equal=64)
    )

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def verify_file_not_exists(self, data, **kwargs):
        """Check that the file does not match anything already in the database."""

        # Check that there is no such file in the database
        project = data.get("project_row")
        try:
            file = (
                models.File.query.filter(
                    sqlalchemy.and_(
                        models.File.name == sqlalchemy.func.binary(data.get("name")),
                        models.File.project_id == sqlalchemy.func.binary(project.id),
                    )
                )
                .with_entities(models.File.id)
                .one_or_none()
            )
        except sqlalchemy.exc.SQLAlchemyError:
            raise

        if file:
            raise FileExistsError

    @marshmallow.post_load
    def return_items(self, data, **kwargs):
        """Create file object."""

        new_file = models.File(
            name=data.get("name"),
            name_in_bucket=data.get("name_in_bucket"),
            subpath=data.get("subpath"),
            size_original=data.get("size"),
            size_stored=data.get("size_processed"),
            compressed=data.get("compressed"),
            salt=data.get("salt"),
            public_key=data.get("public_key"),
            checksum=data.get("checksum"),
        )

        new_version = models.Version(
            size_stored=new_file.size_stored, time_uploaded=utils.current_time()
        )

        project = data.get("project_row")
        # Update foreign keys
        project.file_versions.append(new_version)
        project.files.append(new_file)
        new_file.versions.append(new_version)

        return new_file
