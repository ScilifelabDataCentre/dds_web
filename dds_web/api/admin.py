###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
from flask_restful import fields
import flask
import flask_mail
import flask_restful
import itsdangerous
import marshmallow
import sqlalchemy

# Own modules
from dds_web import app, db, mail
from dds_web.api import errors
from dds_web.crypt import auth
from dds_web.database import models
from dds_web.api import marshmallows

###############################################################################
# MARSHMALLOW ##################################################### MARSHMALLOW #
###############################################################################

invitation_schema = marshmallows.InviteUserSchema()

###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################


class InviteUser(flask_restful.Resource):
    def post(self):
        """Create an invite and send email."""

        try:
            # Use schema to validate and check args
            new_invite = invitation_schema.load(flask.request.args)

            # Add to database
            db.session.add(new_invite)
            db.session.commit()

        except marshmallow.ValidationError as valerr:
            app.logger.info(valerr)
            return flask.jsonify(valerr.messages)
        except sqlalchemy.exc.SQLAlchemyError as sqlerr:
            raise errors.DatabaseError(message=str(sqlerr))

        # Create URL safe token for invitation link
        s = itsdangerous.URLSafeTimedSerializer(app.config["SECRET_KEY"])
        token = s.dumps(new_invite.email, salt="email-confirm")

        # Create link for invitation email
        link = flask.url_for("api_blueprint.confirm_email", token=token, _external=True)

        # Compose and send email
        msg = flask_mail.Message("Confirm email", sender="localhost", recipients=[new_invite.email])
        msg.body = f"Your link is {link}"
        mail.send(msg)

        # TODO: Format response with marshal with?
        return flask.jsonify({"email": new_invite.email})


class ConfirmEmail(flask_restful.Resource):
    def get(self, token):
        """ """

        s = itsdangerous.URLSafeTimedSerializer(app.config["SECRET_KEY"])

        try:
            email = s.loads(token, salt="email-confirm", max_age=20)
        except itsdangerous.exc.SignatureExpired:
            return "The token is expired!"

        return "the token works!"
