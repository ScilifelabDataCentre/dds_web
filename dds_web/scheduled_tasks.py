from datetime import datetime, timedelta

import flask_apscheduler
import flask

from typing import Dict

## Apscheduler
scheduler = flask_apscheduler.APScheduler()


# @scheduler.task("interval", id="reporting", seconds=30, misfire_grace_time=1)
@scheduler.task("cron", id="reporting", day="1", hour=0, minute=1)
def reporting_units_and_users():
    """At the start of every month, get number of units and users."""
    # Imports
    import csv
    import flask_mail
    import flask_sqlalchemy
    import pathlib
    from dds_web import errors, utils
    from dds_web.database.models import User, Unit

    # Get current date
    current_date: str = utils.timestamp(ts_format="%Y-%m-%d")

    # Location of reporting file
    reporting_file: pathlib.Path = pathlib.Path("/code/doc/reporting/dds-reporting.csv")

    # Error default
    error: str = None

    # App context required
    with scheduler.app.app_context():
        # Get email address
        recipient: str = scheduler.app.config.get("MAIL_DDS")
        default_subject: str = "DDS Unit / User report"
        default_body: str = f"This email contains the DDS unit- and user statistics. The data was collected on: {current_date}."
        error_subject: str = f"Error in {default_subject}"
        error_body: str = "The cronjob 'reporting' experienced issues"

        # Get units and count them
        units: flask_sqlalchemy.BaseQuery = Unit.query
        num_units: int = units.count()

        # Count users
        users: flask_sqlalchemy.BaseQuery = User.query
        num_users_total: int = users.count()  # All users
        num_superadmins: int = users.filter_by(type="superadmin").count()  # Super Admins
        num_unit_users: int = users.filter_by(type="unituser").count()  # Unit Admins / Personnel
        num_researchers: int = users.filter_by(type="researchuser").count()  # Researchers
        num_users_excl_superadmins: int = num_users_total - num_superadmins

        # Verify that sum is correct
        if sum([num_superadmins, num_unit_users, num_researchers]) != num_users_total:
            error: str = "Sum of number of users incorrect."
        # Define csv file and verify that it exists
        elif not reporting_file.exists():
            error: str = "Could not find the csv file."

        if error:
            # Send email about error
            file_error_msg: flask_mail.Message = flask_mail.Message(
                subject=error_subject,
                recipients=[recipient],
                body=f"{error_body}: {error}",
            )
            utils.send_email_with_retry(msg=file_error_msg)
            raise Exception(error)

        # Add row with new info
        with reporting_file.open(mode="a") as repfile:
            writer = csv.writer(repfile)
            writer.writerow(
                [
                    current_date,
                    num_units,
                    num_researchers,
                    num_unit_users,
                    num_users_excl_superadmins,
                ]
            )

        # Create email
        msg: flask_mail.Message = flask_mail.Message(
            subject=default_subject,
            recipients=[recipient],
            body=default_body,
        )
        with reporting_file.open(mode="r") as file:  # Attach file
            msg.attach(filename=reporting_file.name, content_type="text/csv", data=file.read())
        utils.send_email_with_retry(msg=msg)  # Send
