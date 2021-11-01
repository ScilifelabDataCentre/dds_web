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
    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, datetime.datetime):
            return value
        return super()._deserialize(value, attr, data, **kwargs)
