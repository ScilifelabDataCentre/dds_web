from datetime import datetime, timedelta
import typing

import flask_apscheduler
import flask

from typing import Dict

## Apscheduler
scheduler = flask_apscheduler.APScheduler()


@scheduler.task("cron", id="available_to_expired", hour=0, minute=1, misfire_grace_time=3600)
# @scheduler.task("interval", id="available_to_expired", seconds=15, misfire_grace_time=1)
def set_available_to_expired():
    scheduler.app.logger.debug("Task: Checking for Expiring projects.")
    import sqlalchemy

    from dds_web import db
    from dds_web.database import models
    from dds_web.errors import DatabaseError
    from dds_web.api.project import ProjectStatus
    from dds_web.utils import current_time, page_query

    with scheduler.app.app_context():
        expire = ProjectStatus()

        errors = {}

        try:
            for unit in db.session.query(models.Unit).with_for_update().all():
                errors[unit.name] = {}

                days_in_expired = unit.days_in_expired

                for project in page_query(
                    db.session.query(models.Project)
                    .filter(
                        sqlalchemy.and_(
                            models.Project.is_active == 1, models.Project.unit_id == unit.id
                        )
                    )
                    .with_for_update()
                ):

                    if (
                        project.current_status == "Available"
                        and project.current_deadline <= current_time()
                    ):
                        scheduler.app.logger.debug("Handling expiring project")
                        scheduler.app.logger.debug(
                            "Project: %s has status %s and expires on: %s",
                            project.public_id,
                            project.current_status,
                            project.current_deadline,
                        )
                        new_status_row = expire.expire_project(
                            project=project,
                            current_time=current_time(),
                            deadline_in=days_in_expired,
                        )

                        project.project_statuses.append(new_status_row)

                        try:
                            db.session.commit()
                            scheduler.app.logger.debug(
                                "Project: %s has status Expired now!", project.public_id
                            )
                        except (
                            sqlalchemy.exc.OperationalError,
                            sqlalchemy.exc.SQLAlchemyError,
                        ) as err:
                            flask.current_app.logger.exception(err)
                            db.session.rollback()
                            errors[unit.name][project.public_id] = str(err)
                        continue
                    else:
                        scheduler.app.logger.debug(
                            "Nothing to do for Project: %s", project.public_id
                        )
        except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.SQLAlchemyError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise

        for unit, projects in errors.items():
            if projects:
                scheduler.app.logger.error(
                    f"Following projects of Unit '{unit}' encountered issues during expiration process:"
                )
                for proj in errors[unit].keys():
                    scheduler.app.logger.error(f"Error for project '{proj}': {errors[unit][proj]} ")


@scheduler.task("cron", id="expired_to_archived", hour=1, minute=1, misfire_grace_time=3600)
# @scheduler.task("interval", id="expired_to_archived", seconds=15, misfire_grace_time=1)
def set_expired_to_archived():
    """Search for expired projects whose deadlines are past and archive them"""

    scheduler.app.logger.debug("Task: Checking for projects to archive.")

    import sqlalchemy
    from dds_web import db
    from dds_web.database import models
    from dds_web.errors import DatabaseError
    from dds_web.utils import current_time, page_query
    from dds_web.api.project import ProjectStatus

    with scheduler.app.app_context():

        archive = ProjectStatus()
        errors = {}

        try:
            for unit in db.session.query(models.Unit).with_for_update().all():
                errors[unit.name] = {}

                for project in page_query(
                    db.session.query(models.Project)
                    .filter(
                        sqlalchemy.and_(
                            models.Project.is_active == 1, models.Project.unit_id == unit.id
                        )
                    )
                    .with_for_update()
                ):

                    if (
                        project.current_status == "Expired"
                        and project.current_deadline <= current_time()
                    ):
                        scheduler.app.logger.debug("Handling project to archive")
                        scheduler.app.logger.debug(
                            "Project: %s has status %s and expired on: %s",
                            project.public_id,
                            project.current_status,
                            project.current_deadline,
                        )
                        new_status_row, delete_message = archive.archive_project(
                            project=project,
                            current_time=current_time(),
                        )
                        scheduler.app.logger.debug(delete_message.strip())
                        project.project_statuses.append(new_status_row)

                        try:
                            db.session.commit()
                            scheduler.app.logger.debug(
                                "Project: %s has status Archived now!", project.public_id
                            )
                        except (
                            sqlalchemy.exc.OperationalError,
                            sqlalchemy.exc.SQLAlchemyError,
                        ) as err:
                            scheduler.app.logger.exception(err)
                            db.session.rollback()
                            errors[unit.name][project.public_id] = str(err)
                        continue
                    else:
                        scheduler.app.logger.debug(
                            "Nothing to do for Project: %s", project.public_id
                        )
        except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.SQLAlchemyError) as err:
            scheduler.app.logger.exception(err)
            db.session.rollback()
            raise

        for unit, projects in errors.items():
            if projects:
                scheduler.app.logger.error(
                    f"Following projects of Unit '{unit}' encountered issues during archival process:"
                )
                for proj in errors[unit].keys():
                    scheduler.app.logger.error(f"Error for project '{proj}': {errors[unit][proj]} ")


@scheduler.task("cron", id="delete_invite", hour=0, minute=1, misfire_grace_time=3600)
# @scheduler.task("interval", id="delete_invite", seconds=15, misfire_grace_time=1)


def delete_invite():
    """Delete invite older than a week"""

    scheduler.app.logger.debug("Task: Checking for invites to delete.")

    from sqlalchemy.exc import OperationalError, SQLAlchemyError
    from dds_web import db
    from dds_web.database import models
    from dds_web.errors import DatabaseError
    from dds_web.utils import current_time

    with scheduler.app.app_context():
        expiration: datetime.datetime = current_time()
        errors: Dict = {}

        try:
            invites: list = db.session.query(models.Invite).all()
            for invite in invites:
                invalid_invite = invite.created_at == "0000-00-00 00:00:00"
                if invalid_invite or (invite.created_at + timedelta(weeks=1)) < expiration:
                    try:
                        db.session.delete(invite)
                        db.session.commit()
                        if invalid_invite:
                            scheduler.app.logger.warning(
                                "Invite with created_at = 0000-00-00 00:00:00 deleted."
                            )
                        else:
                            scheduler.app.logger.debug("Invite deleted.")
                    except (OperationalError, SQLAlchemyError) as err:
                        errors[invite] = str(err)
                        scheduler.app.logger.exception(err)
                        db.session.rollback()
                        continue
        except (OperationalError, SQLAlchemyError) as err:
            scheduler.app.logger.exception(err)
            raise

        for invite, error in errors.items():
            scheduler.app.logger.error(f"{invite} not deleted: {error}")


@scheduler.task(
    "cron", id="get_quarterly_usage", month="Jan,Apr,Jul,Oct", day="1", hour=0, minute=1
)
# @scheduler.task("interval", id="monthly_usage", seconds=60, misfire_grace_time=1)
def quarterly_usage():
    """Get the monthly usage for the units"""

    scheduler.app.logger.debug("Task: Collecting usage information from database.")
    import sqlalchemy

    from dds_web import db
    from dds_web.database import models
    from dds_web.utils import (
        current_time,
        page_query,
        # calculate_period_usage,
        calculate_version_period_usage,
    )

    with scheduler.app.app_context():
        try:
            # 1. Get projects where is_active = False
            # .. a. Check if the versions are all time_deleted == time_invoiced
            # .. b. Yes --> Set new column to True ("done")
            scheduler.app.logger.info("Marking projects as 'done'....")
            for unit, project in page_query(
                db.session.query(models.Unit, models.Project)
                .join(models.Project)
                .filter(models.Project.is_active == False)
            ):
                # Get number of versions in project that have been fully included in usage calcs
                num_done = (
                    db.session.query(models.Project, models.Version)
                    .join(models.Version)
                    .filter(
                        sqlalchemy.and_(
                            models.Project.id == project.id,
                            models.Version.time_deleted == models.Version.time_invoiced,
                        )
                    )
                    .count()
                )

                # Check if there are any versions that are not fully included
                # If not, project is done and should not be included in any more usage calculations in billing
                if num_done == len(project.file_versions):
                    project.done = True

                db.session.commit()

            # 2. Get project where done = False
            for unit, project in page_query(
                db.session.query(models.Unit, models.Project)
                .join(models.Project)
                .filter(models.Project.done == False)
            ):
                project_byte_hours: int = 0
                for version in project.file_versions:
                    # Skipp deleted and already invoiced versions
                    if version.time_deleted == version.time_invoiced and [
                        version.time_deleted,
                        version.time_invoiced,
                    ] != [None, None]:
                        continue
                    version_bhours = calculate_version_period_usage(version=version)
                    project_byte_hours += version_bhours
                scheduler.app.logger.info(
                    f"Project {project.public_id} byte hours: {project_byte_hours}"
                )

                # Create a record in usage table
                new_record = models.Usage(
                    project_id=project.id,
                    usage=project_byte_hours,
                    cost=0,
                    time_collected=current_time(),
                )
                db.session.add(new_record)
                db.session.commit()

        except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.SQLAlchemyError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise


# @scheduler.task(
#     "cron", id="reporting", day="1", hour=0, minute=1
# )
@scheduler.task("interval", id="reporting", seconds=30, misfire_grace_time=1)
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
    reporting_file: pathlib.Path = pathlib.Path("doc/reporting/dds-reporting.csv")

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

        # Verify that sum is correct
        if sum([num_superadmins, num_unit_users, num_researchers]) != num_users_total:
            error: str = "Sum of number of users incorrect."
            # Send email about error
            sum_error_msg: flask_mail.Message = flask_mail.Message(
                subject=error_subject,
                recipients=[recipient],
                body=f"{error_body}: {error}",
            )
            utils.send_email_with_retry(msg=sum_error_msg)
            raise Exception(error)

        # Define csv file and verify that it exists
        if not reporting_file.exists():
            error: str = "Could not find the csv file."
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
                [current_date, num_units, num_researchers, num_unit_users, num_users_total]
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
