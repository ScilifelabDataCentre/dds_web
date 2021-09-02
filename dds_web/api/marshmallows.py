import marshmallow
from dds_web.database import models


class InviteUserSchema(marshmallow.Schema):
    """Schema for InviteUser endpoint"""

    email = marshmallow.fields.Email(required=True)
    account_type = marshmallow.fields.String(
        required=True, validate=marshmallow.validate.OneOf(choices=["Data_Producer", "Recipient"])
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

    @marshmallow.post_load
    def make_invite(self, data, **kwargs):
        """Deserialize to an Invite object"""

        return models.Invite(
            **{
                "email": data.get("email"),
                "is_facility": data.get("account_type") == "Data_Producer",
                "is_researcher": data.get("account_type") == "Recipient",
            }
        )
