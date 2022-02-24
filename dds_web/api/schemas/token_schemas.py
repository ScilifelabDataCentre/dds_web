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
    """Schema for token authentication used when acquiring an encrypted JWT."""

    # Authentication One-Time code
    HOTP = marshmallow.fields.String(
        required=False,
        validate=marshmallow.validate.And(
            marshmallow.validate.Length(min=8, max=8),
            marshmallow.validate.ContainsOnly("0123456789"),
        ),
    )

    TOTP = marshmallow.fields.String(
        required=False,
        validate=marshmallow.validate.And(
            marshmallow.validate.Length(min=6, max=6),
            marshmallow.validate.ContainsOnly("0123456789"),
        ),
    )

    class Meta:
        unknown = marshmallow.EXCLUDE

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def validate_mfa(self, data, **kwargs):
        """Verify HOTP (authentication One-Time code) is correct."""

        # This can be easily extended to require at least one MFA method
        if ("HOTP" not in data) and ("TOTP" not in data):
            raise marshmallow.exceptions.ValidationError("MFA method not supplied")

        user = auth.current_user()

        if user.totp_enabled:
            value = data.get("TOTP")
            if value is None:
                raise marshmallow.ValidationError(
                    "Your account is setup to use TOTP, but you entered a one-time authentication code from email."
                )
            # Raises authentication error if TOTP is incorrect
            user.verify_TOTP(value.encode())
        else:
            value = data.get("HOTP")
            if value is None:
                raise marshmallow.ValidationError(
                    "Your account is setup to use one-time authentication code via email, you cannot authenticate with TOTP."
                )
            # Raises authenticationerror if invalid
            user.verify_HOTP(value.encode())
