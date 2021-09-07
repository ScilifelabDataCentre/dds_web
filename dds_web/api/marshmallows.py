import marshmallow
from dds_web.database import models


class InviteUserSchema(marshmallow.Schema):
    """Schema for InviteUser endpoint"""

    email = marshmallow.fields.Email(required=True)
    role = marshmallow.fields.String(
        required=True,
        validate=marshmallow.validate.OneOf(
            choices=["facility", "researcher"],
        ),
    )
    facility_name = marshmallow.fields.String(required=False)

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

        facility_id = (
            (
                models.Facility.query.filter_by(name=data.get("facility_name"))
                .with_entities(models.Facility.id)
                .first()[0]
            )
            if data.get("facility_name")
            else None
        )

        return models.Invite(
            **{
                "email": data.get("email"),
                "is_facility": data.get("role") == "facility",
                "is_researcher": data.get("role") == "researcher",
                "facility_id": facility_id,
            }
        )
