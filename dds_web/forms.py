"""Forms used in DDS web"""

# IMPORTS ################################################################################ IMPORTS #

# Standard library
import re

# Installed
import flask_wtf
import wtforms
import marshmallow

# Own modules
import dds_web.utils
from dds_web.database import models


# FORMS #################################################################################### FORMS #


def password_contains_valid_characters():
    def _password_contains_valid_characters(form, field):
        """Validate that the password contains valid characters and raise ValidationError."""
        errors = []
        validators = [
            dds_web.utils.contains_uppercase,
            dds_web.utils.contains_lowercase,
            dds_web.utils.contains_digit_or_specialchar,
        ]
        for val in validators:
            try:
                val(input=field.data)
            except marshmallow.ValidationError as valerr:
                errors.append(str(valerr).strip("."))

        if errors:
            raise wtforms.validators.ValidationError(", ".join(errors))

    return _password_contains_valid_characters


class RegistrationForm(flask_wtf.FlaskForm):
    """User registration form."""

    name = wtforms.StringField("name", validators=[wtforms.validators.InputRequired()])
    email = wtforms.StringField(
        "email",
        validators=[wtforms.validators.DataRequired(), wtforms.validators.Email()],
        render_kw={"readonly": True},
    )
    username = wtforms.StringField(
        "username",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Length(min=8, max=20)],
    )
    password = wtforms.PasswordField(
        "password",
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.EqualTo("confirm", message="Passwords must match!"),
            wtforms.validators.Length(min=10, max=64),
            password_contains_valid_characters(),
        ],
    )
    unit_name = wtforms.StringField("unit name")

    confirm = wtforms.PasswordField("Repeat password")
    submit = wtforms.SubmitField("submit")

    def validate_username(self, username):
        user = models.User.query.filter_by(username=username.data).first()
        if user:
            raise wtforms.validators.ValidationError(
                "That username is taken. Please choose a different one."
            )

    def validate_email(self, email):
        email = models.Email.query.filter_by(email=email.data).first()
        if email:
            raise wtforms.validators.ValidationError(
                "That email is taken. Please choose a different one."
            )


class LoginForm(flask_wtf.FlaskForm):
    username = wtforms.StringField(
        "Username",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Length(1, 64)],
    )
    password = wtforms.PasswordField("Password", validators=[wtforms.validators.InputRequired()])
    submit = wtforms.SubmitField("Login")


class LogoutForm(flask_wtf.FlaskForm):
    logout = wtforms.SubmitField("Logout")


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
            password_contains_valid_characters(),
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
