"""Custom marshmallow fields."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import datetime

# Installed
import marshmallow

# Own modules

####################################################################################################
# FIELDS ################################################################################## FIELDS #
####################################################################################################


class MyDateTimeField(marshmallow.fields.DateTime):
    """Custom date time field for marshmallow schemas."""

    def _deserialize(self, value, attr, data, **kwargs):
        """Return a datetime.datetime object as marshmallow field."""
        if isinstance(value, datetime.datetime):
            return value
        return super()._deserialize(value, attr, data, **kwargs)
