###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
import flask
import flask_mail
import flask_restful
import itsdangerous
import sqlalchemy

# Own modules
from dds_web import app, db, mail
from dds_web.crypt import auth
from dds_web.database import models

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################


class InviteUser(flask_restful.Resource):
    def post(self):

        args = flask.request.args
        email = args.get("email")

        try:
            new_invite = models.Invite(email=email)
            db.session.add(new_invite)
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError:
            raise

        s = itsdangerous.URLSafeTimedSerializer(app.config["SECRET_KEY"])
        token = s.dumps(email, salt="email-confirm")

        link = flask.url_for("api_blueprint.confirm_email", token=token, _external=True)
        print(link, flush=True)

        msg = flask_mail.Message("Confirm email", sender="localhost", recipients=[email])
        msg.body = f"Your link is {link}"

        mail.send(msg)
        return flask.jsonify({"email": email, "token": token})


class ConfirmEmail(flask_restful.Resource):
    def get(self, token):
        """ """

        s = itsdangerous.URLSafeTimedSerializer(app.config["SECRET_KEY"])

        try:
            email = s.loads(token, salt="email-confirm", max_age=20)
        except itsdangerous.exc.SignatureExpired:
            return "The token is expired!"

        return "the token works!"
