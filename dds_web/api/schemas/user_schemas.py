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

        return new_invite


class NewUserSchema(marshmallow.Schema):
    """Schema for NewUser endpoint"""

    # TODO: Look through and match to db
    username = marshmallow.fields.String(
        required=True,
        validate=marshmallow.validate.And(
            marshmallow.validate.Length(min=8, max=20),
            utils.valid_chars_in_username,
            # Validation for "username not taken" below
        ),
    )
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
        if invite.role == "Researcher":
            new_user = models.ResearchUser(**common_user_fields)
            # Currently no project associations
        elif invite.role in ["Unit Admin", "Unit Personnel"]:
            new_user = models.UnitUser(**common_user_fields)

            new_user.is_admin = invite.role == "Unit Admin"

            invite.unit.users.append(new_user)
        elif invite.role == "Super Admin":
            new_user = models.SuperAdmin(**common_user_fields)

        # Create new email and append to user relationship
        new_email = models.Email(email=data.get("email"), primary=True)
        new_user.emails.append(new_email)
        new_user.active = True

        db.session.add(new_user)

        # Verify and transfer invite keys to the new user
        new_user.temporary_key = dds_web.security.auth.verify_invite_key(token)
        new_user.nonce = invite.nonce
        new_user.public_key = invite.public_key
        new_user.private_key = invite.private_key
        for project_invite_key in invite.project_invite_keys:
            project_user_key = models.ProjectUserKeys(
                project_id=project_invite_key.project_id,
                user_id=new_user.username,
                key=project_invite_key.key,
            )
            db.session.add(project_user_key)
            db.session.delete(project_invite_key)

        # TODO decrypt the user private key using the temp key,
        #  derive a key from the password and encrypt the user private key with the derived key

        flask.session.pop("invite_token", None)

        # Delete old invite
        db.session.delete(invite)

        # Save and return
        db.session.commit()

        return new_user
