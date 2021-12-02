"""Forms used in DDS web"""

# IMPORTS ################################################################################ IMPORTS #

# Standard library
import re

# Installed
import flask_wtf
import wtforms
import marshmallow

# Own modules
from dds_web import utils
from dds_web.database import models

# FORMS #################################################################################### FORMS #


class RegistrationForm(flask_wtf.FlaskForm):
    """User registration form."""

    name = wtforms.StringField("name", validators=[wtforms.validators.InputRequired()])
    email = wtforms.StringField(
        "email",
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.Email(),
            utils.email_not_taken(),
        ],
        render_kw={"readonly": True},
    )
    username = wtforms.StringField(
        "username",
        validators=[
            wtforms.validators.InputRequired(),
            wtforms.validators.Length(min=8, max=20),
            utils.username_contains_valid_characters(),
            utils.username_not_taken(),
        ],
    )
    password = wtforms.PasswordField(
        "password",
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.EqualTo("confirm", message="Passwords must match!"),
            wtforms.validators.Length(min=10, max=64),
            utils.password_contains_valid_characters(),
        ],
    )
    unit_name = wtforms.StringField("unit name")

    confirm = wtforms.PasswordField("Repeat password")
    submit = wtforms.SubmitField("submit")


class LoginForm(flask_wtf.FlaskForm):
    username = wtforms.StringField(
        "Username",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Length(1, 64)],
    )
    password = wtforms.PasswordField("Password", validators=[wtforms.validators.InputRequired()])
    submit = wtforms.SubmitField("Login")


class LogoutForm(flask_wtf.FlaskForm):
    logout = wtforms.SubmitField("Logout")


# TODO: Remove TwoFactorAuthForm and connected endpoints.
class TwoFactorAuthForm(flask_wtf.FlaskForm):
    secret = wtforms.HiddenField("secret", id="secret")
    otp = wtforms.StringField(
        "otp",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Length(min=6, max=6)],
    )
    submit = wtforms.SubmitField("Authenticate User")


class RequestResetForm(flask_wtf.FlaskForm):
    """Form for attempting password reset."""

    email = wtforms.StringField(
        "Email", validators=[wtforms.validators.DataRequired(), wtforms.validators.Email()]
    )
    submit = wtforms.SubmitField("Request Password Reset")

    def validate_email(self, email):
        """Verify that email adress exists in database."""
        email = models.Email.query.filter_by(email=email.data).first()
        if not email:
            raise wtforms.validators.ValidationError(
                "There is no account with that email. To get an account, you need an invitation."
            )


class ResetPasswordForm(flask_wtf.FlaskForm):
    """Form for setting a new password."""

    password = wtforms.PasswordField(
        "Password",
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.EqualTo("confirm_password", message="Passwords must match!"),
            wtforms.validators.Length(min=10, max=64),
            utils.password_contains_valid_characters(),
        ],
    )
    confirm_password = wtforms.PasswordField(
        "Confirm Password",
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.EqualTo("password", message="The passwords don't match."),
        ],
    )
    submit = wtforms.SubmitField("Reset Password")
