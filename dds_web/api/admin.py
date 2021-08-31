###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
import flask
import flask_restful

# Own modules
from dds_web import app, db
from dds_web.crypt import auth
from dds_web.database import models

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################


class AddUser(flask_restful.Resource):
    def post(self):

        app.logger.info(self)

        new_user = models.User(
            username="new_user",
            password=auth.gen_argon2hash(password="password"),
            role="researcher",
            first_name="New",
            last_name="User",
            facility_id=None,
        )

        db.session.add(new_user)
        db.session.commit()

        return flask.jsonify({"test": "test"})
