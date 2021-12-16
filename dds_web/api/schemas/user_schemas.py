"""User related marshmallow schemas."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
from datetime import datetime

# Installed
import marshmallow
import sqlalchemy
from sqlalchemy.sql.functions import current_user

# Own modules
from dds_web import db
from dds_web.api import errors as ddserr
from dds_web import auth
import dds_web.security.auth
from dds_web.database import models
from dds_web import utils


####################################################################################################
# SCHEMAS ################################################################################ SCHEMAS #
####################################################################################################


class UserSchema(marshmallow.Schema):
    """Schema for User class."""

    email = marshmallow.fields.Email(required=True)

    class Meta:
        unknown = marshmallow.EXCLUDE

    @marshmallow.post_load
    def return_user(self, data, **kwargs):
        """Return the user."""
        email_row = models.Email.query.filter_by(email=data.get("email")).first()
        if not email_row:
            return None

        return email_row.user


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
        elif utils.email_in_db(email=value):
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
    username = marshmallow.fields.String(required=True)
    password = marshmallow.fields.String(
        required=True,
        validate=marshmallow.validate.And(
            marshmallow.validate.Length(min=10, max=64),
            utils.contains_digit_or_specialchar,
            utils.contains_lowercase,
            utils.contains_uppercase,
        ),
    )
    email = marshmallow.fields.Email(
        required=True,
        validate=marshmallow.validate.And(marshmallow.validate.Email(), utils.email_not_taken),
    )
    name = marshmallow.fields.String(required=True, validate=marshmallow.validate.Length(max=255))

    class Meta:
        """Exclude unknown fields e.g. csrf etc that are passed with form"""

        unknown = marshmallow.EXCLUDE

    @marshmallow.validates("username")
    def verify_username(self, value):
        """Verify that the username is not used in the system."""

        if utils.username_in_db(username=value):
            raise marshmallow.ValidationError(
                message=(
                    f"The username '{value}' is already taken by another user. "
                    "Try something else."
                )
            )

    @marshmallow.validates("email")
    def verify_new_email(self, value):
        """Verify that the email is not used in the system already."""

        if utils.email_in_db(email=value):
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

        common_user_fields = {
            "username": data.get("username"),
            "password": data.get("password"),
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
