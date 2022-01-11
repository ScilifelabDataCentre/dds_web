"""MFA related marshmallow schema."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library

# Installed
import marshmallow

# Own modules
from dds_web import auth


####################################################################################################
# SCHEMA ################################################################################## SCHEMA #
####################################################################################################


class TokenSchema(marshmallow.Schema):
    """Schema for token authentication used when acquiring a token."""

    HOTP = marshmallow.fields.String(
        required=False,
        validate=marshmallow.validate.And(
            marshmallow.validate.Length(min=8, max=8),
            marshmallow.validate.ContainsOnly("0123456789"),
        ),
    )

    class Meta:
        unknown = marshmallow.EXCLUDE

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def validate_mfa(self, data, **kwargs):
        """Verify HOTP is correct."""

        # This can be easily extended to require at least one MFA method

        if "HOTP" not in data:
            raise marshmallow.ValidationError("MFA method not supplied")

        user = auth.current_user()
        user.verify_HOTP(value)
