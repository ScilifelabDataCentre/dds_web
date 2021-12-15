"""Forms used in DDS web"""

# IMPORTS ################################################################################ IMPORTS #

# Standard library
import re

# Installed
import flask_wtf
import flask_login
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
            utils.email_not_taken_wtforms(),
        ],
        render_kw={"readonly": True},
    )
    username = wtforms.StringField(
        "username",
        validators=[
            wtforms.validators.InputRequired(),
            wtforms.validators.Length(min=8, max=20),
            utils.username_contains_valid_characters(),
            utils.username_not_taken_wtforms(),
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

    confirm = wtforms.PasswordField(
        "Repeat Password",
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.EqualTo("password", message="The passwords don't match."),
        ],
    )
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
    """Form for attempting password reset when old password is lost."""

    email = wtforms.StringField(
        "Email",
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.Email(),
            utils.email_taken_wtforms(),
        ],
    )
    submit = wtforms.SubmitField("Request Password Reset")


class ResetPasswordForm(flask_wtf.FlaskForm):
    """Form for setting a new password when old password is lost."""

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
        "Repeat Password",
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.EqualTo("password", message="The passwords don't match."),
        ],
    )
    submit = wtforms.SubmitField("Reset Password")


class ChangePasswordForm(flask_wtf.FlaskForm):
    """Form for setting a new password using the old password."""

    current_password = wtforms.PasswordField(
        "Current Password",
        validators=[wtforms.validators.DataRequired()],
    )
    new_password = wtforms.PasswordField(
        "New Password",
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.EqualTo("confirm_new_password", message="Passwords must match!"),
            wtforms.validators.Length(min=10, max=64),
            utils.password_contains_valid_characters(),
        ],
    )
    confirm_new_password = wtforms.PasswordField(
        "Repeat New Password",
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.EqualTo("new_password", message="The passwords don't match."),
        ],
    )

    def validate_current_password(form, field):
        if not flask_login.current_user.verify_password(form.current_password.data):
            raise wtforms.ValidationError("Entered current password is incorrect!")

    submit = wtforms.SubmitField("Change Password")
