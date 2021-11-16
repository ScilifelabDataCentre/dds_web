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
        "email", validators=[wtforms.validators.Email()], render_kw={"readonly": True}
    )
    username = wtforms.StringField(
        "username",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Length(min=8, max=20)],
    )
    password = wtforms.PasswordField(
        "password",
        validators=[
            wtforms.validators.InputRequired(),
            wtforms.validators.EqualTo("confirm", message="Passwords must match!"),
            wtforms.validators.Length(min=10, max=64),
            password_contains_valid_characters(),
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
