"""Marshmallow schemas used by the DDS"""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library

# Installed
import flask
import marshmallow
import sqlalchemy
import immutabledict

# Own modules
from dds_web import db
from dds_web.api import errors as ddserr
from dds_web import auth
from dds_web.database import models

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
        raise ddserr.NoSuchProjectError

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


class InviteUserSchema(marshmallow.Schema):
    """Schema for InviteUser endpoint"""

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
            raise marshmallow.ValidationError(f"Email '{value}' already has a pending invitation.")
        elif models.Email.query.filter_by(email=value).first():
            raise marshmallow.ValidationError(
                f"The email '{value}' is already registered to an existing user."
            )

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def validate_user_invite_permissions(self, data, **kwargs):
        """Validate current users permissions to invite specified role."""

        curr_user_role = auth.current_user().role
        attempted_invite_role = data.get("role")
        if curr_user_role == "Unit Admin":
            if attempted_invite_role == "Super Admin":
                raise marshmallow.ValidationError("permission to invite denied")
        elif curr_user_role == "Unit Personnel":
            if attempted_invite_role in ["Super Admin", "Unit Admin"]:
                raise marshmallow.ValidationError("permission to invite denied")
        elif curr_user_role == "Researcher":
            # research users can only invite in certain projects if they are set as the owner
            # TODO: Add required project field for researchers to be able to invite (if owner)
            raise marshmallow.ValidationError("permission to invite denied")

    @marshmallow.post_load
    def make_invite(self, data, **kwargs):
        """Deserialize to an Invite object"""

        if data.get("role") == "Super Admin":
            # TODO: here the unit needs to be specified
            raise marshmallow.ValidationError("currently not creating invites for superadmins")

        # Create and return invite row
        new_invite = models.Invite(**{"email": data.get("email"), "role": data.get("role")})
        auth.current_user().unit.invites.append(new_invite)

        return new_invite


class NewUserSchema(marshmallow.Schema):
    """Schema for NewUser endpoint"""

    # TODO: Look through and match to db
    username = marshmallow.fields.String(
        required=True,
        validate=marshmallow.validate.Regexp(
            regex="^[[:alnum:]-]{6,25}$",
            # username must only contain alphanumeric characters and hyphens and must be between 6-25 characters long
            # \p{Pd} could be used to match any kind of dash instead of just the hyphen.
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
    first_name = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(max=50)
    )
    last_name = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(max=50)
    )

    facility_name = marshmallow.fields.String(required=False)

    class Meta:
        """Exclude unknown fields e.g. csrf etc that are passed with form"""

        unknown = marshmallow.EXCLUDE

    @marshmallow.pre_load
    def hash_password(self, in_data, **_):

        if not in_data.get("password"):
            raise marshmallow.ValidationError("Password required to create users.")

        in_data["password"] = auth.gen_argon2hash(password=in_data.get("password"))

        return in_data

    @marshmallow.post_load
    def make_user(self, data, **kwargs):
        """Deserialize to an User object"""

        # Get facility row
        facility = (
            (models.Facility.query.filter_by(name=data.get("facility_name")).first())
            if data.get("facility_name")
            else None
        )

        # Create new user row
        new_user = models.User(
            **{
                "username": data.get("username"),
                "password": data.get("password"),
                "role": data.get("role") == "facility" if facility else "researcher",
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "facility_id": facility.id if facility else None,
            }
        )

        # Create new email and append to user relationship
        new_email = models.Email(email=data.get("email"), primary=True, user=new_user)
        new_user.emails.append(new_email)

        # Delete old invite
        old_email = models.Invite.query.filter(models.Invite.email == new_email.email).first()
        db.session.delete(old_email)

        # Append user to facility users
        if facility:
            facility.users.append(new_user)

        db.session.add(new_user)
        db.session.commit()

        return new_user.username
