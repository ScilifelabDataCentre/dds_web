"""Forms used in DDS web"""

# IMPORTS ################################################################################ IMPORTS #

# Standard library

# Installed
import flask_wtf
import flask_login
import wtforms

# Own modules
from dds_web import utils

# FORMS #################################################################################### FORMS #


class RegistrationForm(flask_wtf.FlaskForm):
    """User registration form."""

    name = wtforms.StringField(
        "Name",
        validators=[
            wtforms.validators.Length(
                min=2, message="The name must be at least 2 characters long."
            ),
            wtforms.validators.InputRequired(message="Please enter your full name."),
        ],
    )
    email = wtforms.StringField(
        "Email",
        validators=[
            wtforms.validators.DataRequired(message="You need to provide an email address."),
            wtforms.validators.Email(message="Please provide a valid email (the one invited)."),
            utils.email_not_taken_wtforms(),
        ],
        render_kw={"readonly": True},
    )
    username = wtforms.StringField(
        "Username",
        validators=[
            wtforms.validators.InputRequired(message="Please enter a username."),
            wtforms.validators.Length(
                min=3, max=30, message="The username must be between 3 and 30 characters long."
            ),
            utils.username_contains_valid_characters(),
            utils.username_not_taken_wtforms(),
        ],
    )
    password = wtforms.PasswordField(
        "Password",
        validators=[
            wtforms.validators.DataRequired(message="You need to provide a password."),
            wtforms.validators.EqualTo("confirm", message="The passwords do not match."),
            wtforms.validators.Length(
                min=10, max=64, message="The password must be between 10 and 64 characters long."
            ),
            utils.password_contains_valid_characters(),
        ],
    )

    confirm = wtforms.PasswordField(
        "Repeat Password",
        validators=[
            wtforms.validators.DataRequired(message="Please repeat the password."),
            wtforms.validators.EqualTo("password", message="The passwords do not match."),
        ],
    )
    submit = wtforms.SubmitField("submit")


class LoginForm(flask_wtf.FlaskForm):
    username = wtforms.StringField(
        "Username",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Length(1, 64)],
    )
    password = wtforms.PasswordField("Password", validators=[wtforms.validators.InputRequired()])
    submit = wtforms.SubmitField("Log in")


class LogoutForm(flask_wtf.FlaskForm):
    logout = wtforms.SubmitField("Logout")


class Confirm2FACodeHOTPForm(flask_wtf.FlaskForm):
    hotp = wtforms.StringField(
        "Multi-factor authentication code",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Length(min=8, max=8)],
    )
    submit = wtforms.SubmitField("Authenticate")


class Confirm2FACodeTOTPForm(flask_wtf.FlaskForm):
    totp = wtforms.StringField(
        "totp",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Length(min=6, max=6)],
    )
    submit = wtforms.SubmitField("Authenticate")


class ActivateTOTPForm(flask_wtf.FlaskForm):
    totp = wtforms.StringField(
        "totp",
        validators=[wtforms.validators.InputRequired(), wtforms.validators.Length(min=6, max=6)],
    )
    submit = wtforms.SubmitField("Activate")


class Cancel2FAForm(flask_wtf.FlaskForm):
    cancel = wtforms.SubmitField("Cancel login and try again")


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
