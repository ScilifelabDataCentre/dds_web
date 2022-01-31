"Utility functions and classes useful within the DDS."

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import datetime
import json
import os
import pathlib
import re
import urllib.parse

# Installed
import pandas
from contextlib import contextmanager
import flask
import flask_mail
import flask_login
import sqlalchemy

# # imports related to scheduling
import atexit
import werkzeug
from apscheduler.schedulers import background
import marshmallow
import flask_mail
import wtforms


# Own modules
from dds_web.database import models
from dds_web import auth, db, mail

####################################################################################################
# VALIDATORS ########################################################################## VALIDATORS #
####################################################################################################

# General ################################################################################ General #


def contains_uppercase(input):
    """Verify that string contains at least one upper case letter."""
    if not re.search("[A-Z]", input):
        raise marshmallow.ValidationError("Required: at least one upper case letter.")


def contains_lowercase(input):
    """Verify that string contains at least one lower case letter."""
    if not re.search("[a-z]", input):
        raise marshmallow.ValidationError("Required: at least one lower case letter.")


def contains_digit_or_specialchar(input):
    """Verify that string contains at least one special character OR digit."""
    if not any(re.search(x, input) for x in ["[0-9]", "[#?!@$%^&*-]"]):
        raise marshmallow.ValidationError(
            "Required: at least one digit OR a special character (#?!@$%^&*-)."
        )


def email_not_taken(input):
    """Validator - verify that email is not taken.

    If used by marshmallow Schema, this validator should never raise an error since the email
    field should not be changable and if it is the form validator should catch it.
    """
    if email_in_db(email=input):
        raise marshmallow.validate.ValidationError("The email is already taken by another user.")


def email_taken(input):
    """Validator - verify that email is taken."""
    if not email_in_db(email=input):
        raise marshmallow.validate.ValidationError(
            "There is no account with that email. To get an account, you need an invitation."
        )


def username_not_taken(input):
    """Validate that username is not taken.

    If used by marshmallow Schema, this validator should never raise an error since
    the form validator should catch it.
    """
    if username_in_db(username=input):
        raise marshmallow.validate.ValidationError(
            "That username is taken. Please choose a different one."
        )


# wtforms ################################################################################ wtforms #


def username_contains_valid_characters():
    def _username_contains_valid_characters(form, field):
        """Validate that the username contains valid characters."""
        if not valid_chars_in_username(input=field.data):
            raise wtforms.validators.ValidationError(
                "The username contains invalid characters. "
                "Usernames can only contain letters, digits and underscores (_)."
            )

    return _username_contains_valid_characters


def password_contains_valid_characters():
    def _password_contains_valid_characters(form, field):
        """Validate that the password contains valid characters and raise ValidationError."""
        errors = []
        validators = [
            contains_uppercase,
            contains_lowercase,
            contains_digit_or_specialchar,
        ]
        for val in validators:
            try:
                val(input=field.data)
            except marshmallow.ValidationError as valerr:
                errors.append(str(valerr).strip("."))

        if errors:
            raise wtforms.validators.ValidationError(", ".join(errors))

    return _password_contains_valid_characters


def username_not_taken_wtforms():
    def _username_not_taken(form, field):
        """Validate that the username is not taken already."""
        try:
            username_not_taken(input=field.data)
        except marshmallow.validate.ValidationError as valerr:
            raise wtforms.validators.ValidationError(valerr)

    return _username_not_taken


def email_not_taken_wtforms():
    def _email_not_taken(form, field):
        """Validate that the email is not taken already."""
        try:
            email_not_taken(input=field.data)
        except marshmallow.validate.ValidationError as valerr:
            raise wtforms.validators.ValidationError(valerr)

    return _email_not_taken


def email_taken_wtforms():
    def _email_taken(form, field):
        """Validate that the email exists."""
        try:
            email_taken(input=field.data)
        except marshmallow.validate.ValidationError as valerr:
            raise wtforms.validators.ValidationError(valerr)

    return _email_taken


####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def valid_chars_in_username(input):
    """Check if the username contains only valid characters."""
    pattern = re.compile("^[a-zA-Z0-9_]+$")
    return string_contains_only(input=input, pattern=pattern)


def string_contains_only(input, pattern):
    """Check if string only contains specific characters."""
    if re.search(pattern, input):
        return True

    return False


def email_in_db(email):
    """Check if the email is in the Email table."""
    if models.Email.query.filter_by(email=email).first():
        return True

    return False


def username_in_db(username):
    """Check if username is in the User table."""
    if models.User.query.filter_by(username=username).first():
        return True

    return False


def get_username_or_request_ip():
    """Util function for action logger: Try to identify the requester"""

    if auth.current_user():
        current_user = auth.current_user().username
    elif flask_login.current_user.is_authenticated:
        current_user = flask_login.current_user.username
    else:
        username = (
            flask.request.authorization.get("username") if flask.request.authorization else "---"
        )
        if flask.request.remote_addr:
            current_user = f"{username} ({flask.request.remote_addr})"  # log IP instead of username
        elif flask.request.access_route:
            current_user = (
                f"{username} ({flask.request.access_route[0]})"  # log IP instead of username
            )
        else:
            current_user = f"{username} (anonymous)"

    return current_user


def delrequest_exists(email):
    """Check if there is already a deletion request for that email."""
    if models.DeletionRequest.query.filter_by(email=email).first():
        return True
    return False


def send_reset_email(email_row):
    """Generate password reset email."""
    # Generate token
    token = email_row.user.get_reset_token()

    # Create and send email
    message = flask_mail.Message(
        "Password Reset Request",
        sender=flask.current_app.config.get("MAIL_SENDER", "dds@noreply.se"),
        recipients=[email_row.email],
    )
    message.body = (
        "To reset your password, visit the following link: "
        f"{flask.url_for('auth_blueprint.reset_password', token=token, _external=True)}"
        "If you did not make this request then simply ignore this email and no changes will be made."
    )
    mail.send(message)


def is_safe_url(target):
    """Check if the url is safe for redirects."""
    ref_url = urllib.parse.urlparse(flask.request.host_url)
    test_url = urllib.parse.urlparse(urllib.parse.urljoin(flask.request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def current_time(to_midnight=False):
    """Return the current time for UTC"""

    curr_time = datetime.datetime.utcnow()
    if to_midnight:
        curr_time = curr_time.replace(hour=23, minute=59, second=59)

    return curr_time


def timestamp(dts=None, datetime_string=None, ts_format="%Y-%m-%d %H:%M:%S.%f%z"):
    """Gets the current time. Formats timestamp.

    Returns:
        str:    Timestamp in format 'YY-MM-DD_HH-MM-SS'

    """

    # print(f"\nTime stamp : {datetime.datetime.utcnow}\n")
    if datetime_string is not None:
        datetime_stamp = datetime.datetime.strptime(datetime_string, ts_format)
        return str(datetime_stamp.date())

    now = current_time() if dts is None else dts
    t_s = str(now.strftime(ts_format))
    return t_s


def rate_limit_from_config():
    return flask.current_app.config.get("TOKEN_ENDPOINT_ACCESS_LIMIT", "10/hour")


@contextmanager
def working_directory(path, cleanup_after=False):
    """Contexter for changing working directory"""
    current_path = os.getcwd()
    try:
        if not os.path.exists(path):
            os.mkdir(path)
        os.chdir(path)
        yield
    finally:
        os.chdir(current_path)


def format_byte_size(size):
    """Take size in bytes and converts according to the size"""
    suffixes = ["bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]

    for suffix in suffixes:
        if size >= 1000:
            size /= 1000
        else:
            break

    return f"{size:.2} {suffix}" if isinstance(size, float) else f"{size} {suffix}"


def page_query(q):
    offset = 0
    while True:
        r = False
        for elem in q.limit(1000).offset(offset):
            r = True
            yield elem
        offset += 1000
        if not r:
            break


def create_one_time_password_email(user, hotp_value):
    msg = flask_mail.Message(
        "DDS One-Time Authentication Code",
        sender=flask.current_app.config.get("MAIL_SENDER", "dds@noreply.se"),
        recipients=[user.primary_email],
    )

    msg.attach(
        "scilifelab_logo.png",
        "image/png",
        open(os.path.join(flask.current_app.static_folder, "img/scilifelab_logo.png"), "rb").read(),
        "inline",
        headers=[
            ["Content-ID", "<Logo>"],
        ],
    )
    msg.body = flask.render_template(
        "mail/authenticate.txt", one_time_value=hotp_value.decode("utf-8")
    )
    msg.html = flask.render_template(
        "mail/authenticate.html", one_time_value=hotp_value.decode("utf-8")
    )

    return msg


####################################################################################################
# BACKGROUND SCHEDULER ###################################################### BACKGROUND SCHEDULER #
####################################################################################################


def scheduler_wrapper():

    # Flask in debug mode spawns a child process so that it can restart the process each time the code changes,
    # the new child process initializes and starts a new APScheduler, causing the jobs to be created twice
    # within in the same database table:
    # pymysql.err.IntegrityError: (1062, "Duplicate entry 'calc_costs' for key 'PRIMARY'") error

    # Apparently, the reload is done with a subprocess.call, so we have 2 different Python interpreters running at the same time!
    # This also means that any if statement or replace_existing=FALSE paramenter in add_job() won't prevent these errors.
    # This if statement hopefully solves the issue:

    if flask.helpers.get_debug_flag() and not werkzeug.serving.is_running_from_reloader():
        return

    scheduler = background.BackgroundScheduler(
        {
            "apscheduler.jobstores.default": {
                "type": "sqlalchemy",
                # "url": flask.current_app.config.get("SQLALCHEMY_DATABASE_URI"),
                "engine": db.engine,
            },
            "apscheduler.timezone": "Europe/Stockholm",
        }
    )

    scheduler.start()
    flask.current_app.logger.info("Started main scheduler")

    # Extract all jobIDs currently scheduled
    joblist = scheduler.get_jobs()
    jobid = []
    for job in joblist:
        id = getattr(job, "id")
        jobid.append(id)

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

    # Print the currently scheduled jobs as verification:
    joblist = scheduler.get_jobs()
    flask.current_app.logger.info("Currently scheduled jobs:")
    for job in joblist:
        flask.current_app.logger.info(f"Job: {job}")
