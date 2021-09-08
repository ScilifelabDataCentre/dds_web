"""Marshmallow schemas used by the DDS"""

# IMPORTS ################################################################################ IMPORTS #

# Standard library

# Installed
import marshmallow

# Own modules
from dds_web import db
from dds_web.database import models
from dds_web.crypt import auth

# SCHEMAS ################################################################################ SCHEMAS #


class InviteUserSchema(marshmallow.Schema):
    """Schema for InviteUser endpoint"""

    email = marshmallow.fields.Email(required=True)  # Validator below
    facility_name = marshmallow.fields.String(required=False)  # Validator below
    role = marshmallow.fields.String(
        required=True,
        validate=marshmallow.validate.OneOf(
            choices=["facility", "researcher"],
        ),
    )

    @marshmallow.pre_load
    def verify_existing_facility(self, in_data, **_):
        """Check that the facility name is specified if the role is facility"""

        if in_data.get("role") == "facility" and not in_data.get("facility_name"):
            raise marshmallow.ValidationError("Facility name required when adding facility user.")

        return in_data

    @marshmallow.validates("email")
    def validate_email(self, value):
        """Check that email is not used by anyone in db."""

        if models.Invite.query.filter_by(email=value).first():
            raise marshmallow.ValidationError(f"Email '{value}' already has a pending invitation.")
        elif models.Email.query.filter_by(email=value).first():
            raise marshmallow.ValidationError(
                f"The email '{value}' is already registered to an existing user."
            )

    @marshmallow.validates("facility_name")
    def validate_facility_name(self, value):
        """Check that facility is filled in and that it exists in the database"""

        if not models.Facility.query.filter_by(name=value).first():
            raise marshmallow.ValidationError(f"Facility '{value}' does not exist.")

    @marshmallow.post_load
    def make_invite(self, data, **kwargs):
        """Deserialize to an Invite object"""

        # Get facility id for foreign key in invite
        facility_id = (
            (
                models.Facility.query.filter_by(name=data.get("facility_name"))
                .with_entities(models.Facility.id)
                .first()[0]
            )
            if data.get("facility_name")
            else None
        )

        # Create and return invite row
        return models.Invite(
            **{
                "email": data.get("email"),
                "is_facility": data.get("role") == "facility",
                "is_researcher": data.get("role") == "researcher",
                "facility_id": facility_id,
            }
        )


class NewUserSchema(marshmallow.Schema):
    """Schema for NewUser endpoint"""

    # TODO: Look through and match to db
    username = marshmallow.fields.String(required=True)
    password = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.Length(max=120)
    )
    email = marshmallow.fields.Email(required=True)
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
