"""User related marshmallow schemas."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Installed
import flask
import marshmallow
import sqlalchemy

# Own modules
import dds_web
from dds_web import auth, db, utils
from dds_web import errors as ddserr
from dds_web.database import models
from dds_web.security.project_user_keys import verify_and_transfer_invite_to_user

####################################################################################################
# SCHEMAS ################################################################################ SCHEMAS #
####################################################################################################


class UserSchema(marshmallow.Schema):
    """Schema for User class."""

    email = marshmallow.fields.Email(
        required=True,
        allow_none=False,
        error_messages={
            "required": {"message": "A user email is required."},
            "null": {"message": "The user email cannot be null."},
        },
    )

    class Meta:
        unknown = marshmallow.EXCLUDE

    @marshmallow.post_load
    def return_user(self, data, **kwargs):
        """Return the user."""

        email_row = models.Email.query.filter_by(email=data.get("email")).first()
        if not email_row:
            return None

        return email_row.user


class UnansweredInvite(marshmallow.Schema):
    """Schema to return an unanswered invite."""

    email = marshmallow.fields.Email(
        required=True,
        allow_none=False,
        error_messages={
            "required": {"message": "An email is required."},
            "null": {"message": "The email cannot be null."},
        },
    )

    class Meta:
        unknown = marshmallow.EXCLUDE

    @marshmallow.post_load
    def return_invite(self, data, **kwargs):
        """Return the invite object."""
        # returns the invite, if there is exactly one or raises an exception.
        # returns none, if there is no invite
        invite = models.Invite.query.filter_by(email=data.get("email")).one_or_none()

        # double check if there is no existing user with this email
        userexists = utils.email_in_db(email=data.get("email"))

        if userexists and invite:
            raise ddserr.DatabaseError(message="Email exists for user and invite at the same time")

        # if the user exists already, the invite object must not be returned to prevent sign-up
        return invite if not userexists else None


class NewUserSchema(marshmallow.Schema):
    """Schema for NewUser endpoint"""

    # TODO: Look through and match to db
    username = marshmallow.fields.String(
        required=True,
        allow_none=False,
        validate=marshmallow.validate.And(
            marshmallow.validate.Length(min=3, max=30),
            utils.valid_chars_in_username,
            # Validation for "username not taken" below
        ),
        error_messages={
            "required": {"message": "A username is required."},
            "null": {"message": "The username cannot be null."},
        },
    )
    password = marshmallow.fields.String(
        required=True,
        allow_none=False,
        validate=marshmallow.validate.And(
            marshmallow.validate.Length(min=10, max=64),
            utils.contains_digit_or_specialchar,
            utils.contains_lowercase,
            utils.contains_uppercase,
        ),
        error_messages={
            "required": {"message": "A password is required."},
            "null": {"message": "The password cannot be null."},
        },
    )
    email = marshmallow.fields.Email(
        required=True,
        allow_none=False,
        validate=marshmallow.validate.And(marshmallow.validate.Email(), utils.email_not_taken),
        error_messages={
            "required": {"message": "An email is required."},
            "null": {"message": "The email cannot be null."},
        },
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
                message=f"The username '{value}' is already taken by another user. "
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
            raise ddserr.InviteError(
                message="No invite has been found for this email at schema validation"
            )

        data["invite"] = invite

    @marshmallow.post_load
    def make_user(self, data, **kwargs):
        """Deserialize to an User object"""
        token = flask.session.get("invite_token")
        if not dds_web.security.auth.matching_email_with_invite(token, data.get("email")):
            raise ddserr.InviteError(message="Form email and token email are not the same")

        common_user_fields = {
            "username": data.get("username"),
            "password": data.get("password"),
            "name": data.get("name"),
        }

        # Create new user

        invite = data.get("invite")
        if invite.role == "Super Admin":
            new_user = models.SuperAdmin(**common_user_fields)
        elif invite.role in ["Unit Admin", "Unit Personnel"]:
            new_user = models.UnitUser(**common_user_fields)

            new_user.is_admin = invite.role == "Unit Admin"

            invite.unit.users.append(new_user)
        elif invite.role == "Researcher":
            new_user = models.ResearchUser(**common_user_fields)

        # Create new email and append to user relationship
        new_email = models.Email(email=data.get("email"), primary=True)
        new_user.emails.append(new_email)
        new_user.active = True

        db.session.add(new_user)

        # Verify and transfer invite keys to the new user
        if verify_and_transfer_invite_to_user(token, new_user, data.get("password")):
            for project_invite_key in invite.project_invite_keys:
                if isinstance(new_user, models.ResearchUser):
                    project_user = models.ProjectUsers(
                        project_id=project_invite_key.project_id, owner=project_invite_key.owner
                    )
                    new_user.project_associations.append(project_user)

                project_user_key = models.ProjectUserKeys(
                    project_id=project_invite_key.project_id,
                    user_id=new_user.username,
                    key=project_invite_key.key,
                )
                db.session.add(project_user_key)
                db.session.delete(project_invite_key)

            flask.session.pop("invite_token", None)

            # Delete old invite
            db.session.delete(invite)

            # Save and return
            db.session.commit()

            return new_user

        flask.session.pop("invite_token", None)
        db.session.delete(new_user)
        db.session.commit()
        raise ddserr.InviteError(message="Invite key verification has failed!")
