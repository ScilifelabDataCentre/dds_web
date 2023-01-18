"""Flask commands runable in container."""

# Imports

# Standard
import os
import re
import sys
import datetime

# Installed
import click
import flask
import sqlalchemy

# Own
from dds_web import db


@click.command("init-db")
@click.argument("db_type", type=click.Choice(["production", "dev-small", "dev-big"]))
@flask.cli.with_appcontext
def fill_db_wrapper(db_type):
    """Add necessary information to the initial database depending on if in dev or prod."""
    from dds_web.database import models

    if db_type == "production":
        username = flask.current_app.config["SUPERADMIN_USERNAME"]
        password = flask.current_app.config["SUPERADMIN_PASSWORD"]
        name = flask.current_app.config["SUPERADMIN_NAME"]
        existing_user = models.User.query.filter_by(username=username).one_or_none()

        email = flask.current_app.config["SUPERADMIN_EMAIL"]
        existing_email = models.Email.query.filter_by(email=email).one_or_none()

        if existing_email:
            flask.current_app.logger.info(
                f"User with email '{email}' already exists, not creating user."
            )
        elif existing_user:
            if isinstance(existing_user, models.SuperAdmin):
                flask.current_app.logger.info(
                    f"Super admin with username '{username}' already exists, not creating user."
                )
        else:
            flask.current_app.logger.info(f"Adding Super Admin: {username} ({email})")
            new_super_admin = models.SuperAdmin(username=username, name=name, password=password)
            new_email = models.Email(email=email, primary=True)
            new_email.user = new_super_admin
            db.session.add(new_email)
            db.session.commit()
            flask.current_app.logger.info(f"Super Admin added: {username} ({email})")
    else:
        flask.current_app.logger.info("Initializing development db")
        assert flask.current_app.config["USE_LOCAL_DB"]

        if db_type == "dev-small":
            from dds_web.development.db_init import fill_db

            fill_db()
        elif db_type == "dev-big":
            import dds_web.development.factories

            dds_web.development.factories.create_all()

        flask.current_app.logger.info("DB filled")


@click.command("create-unit")
@click.option("--name", "-n", type=str, required=True)
@click.option("--public_id", "-p", type=str, required=True)
@click.option("--external_display_name", "-e", type=str, required=True)
@click.option("--contact_email", "-c", type=str, required=True)
@click.option("--internal_ref", "-ref", type=str, required=False)
@click.option("--safespring_endpoint", "-se", type=str, required=True)
@click.option("--safespring_name", "-sn", type=str, required=True)
@click.option("--safespring_access", "-sa", type=str, required=True)
@click.option("--safespring_secret", "-ss", type=str, required=True)
@click.option("--days_in_available", "-da", type=int, required=False, default=90)
@click.option("--days_in_expired", "-de", type=int, required=False, default=30)
@flask.cli.with_appcontext
def create_new_unit(
    name,
    public_id,
    external_display_name,
    contact_email,
    internal_ref,
    safespring_endpoint,
    safespring_name,
    safespring_access,
    safespring_secret,
    days_in_available,
    days_in_expired,
):
    """Create a new unit.

    Rules for bucket names, which are affected by the public_id at the moment:
    https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
    """
    from dds_web.database import models

    error_message = ""
    if len(public_id) > 50:
        error_message = "The 'public_id' can be a maximum of 50 characters"
    elif re.findall(r"[^a-zA-Z0-9.-]", public_id):
        error_message = (
            "The 'public_id' can only contain letters, numbers, dots (.) and hyphens (-)."
        )
    elif public_id[0] in [".", "-"]:
        error_message = "The 'public_id' must begin with a letter or number."
    elif public_id.count(".") > 2:
        error_message = "The 'public_id' should not contain more than two dots."
    elif public_id.startswith("xn--"):
        error_message = "The 'public_id' cannot begin with the 'xn--' prefix."

    if error_message:
        flask.current_app.logger.error(error_message)
        return

    new_unit = models.Unit(
        name=name,
        public_id=public_id,
        external_display_name=external_display_name,
        contact_email=contact_email,
        internal_ref=internal_ref or public_id,
        safespring_endpoint=safespring_endpoint,
        safespring_name=safespring_name,
        safespring_access=safespring_access,
        safespring_secret=safespring_secret,
        days_in_available=days_in_available,
        days_in_expired=days_in_expired,
    )
    db.session.add(new_unit)
    db.session.commit()

    flask.current_app.logger.info(f"Unit '{name}' created")


@click.command("update-uploaded-file")
@click.option("--project", "-p", type=str, required=True)
@click.option("--path-to-log-file", "-fp", type=str, required=True)
@flask.cli.with_appcontext
def update_uploaded_file_with_log(project, path_to_log_file):
    """Update file details that weren't properly uploaded to db from cli log"""
    import botocore
    from dds_web.database import models
    from dds_web import db
    from dds_web.api.api_s3_connector import ApiS3Connector
    import json

    proj_in_db = models.Project.query.filter_by(public_id=project).one_or_none()
    if not proj_in_db:
        flask.current_app.logger.error(f"The project '{project}' doesn't exist.")
        return

    if not os.path.exists(path_to_log_file):
        flask.current_app.logger.error(f"The log file '{path_to_log_file}' doesn't exist.")
        return

    with open(path_to_log_file, "r") as f:
        log = json.load(f)
    errors = {}
    files_added = []
    for file, vals in log.items():
        status = vals.get("status")
        if not status or not status.get("failed_op") == "add_file_db":
            continue

        with ApiS3Connector(project=proj_in_db) as s3conn:
            try:
                _ = s3conn.resource.meta.client.head_object(
                    Bucket=s3conn.project.bucket, Key=vals["path_remote"]
                )
            except botocore.client.ClientError as err:
                if err.response["Error"]["Code"] == "404":
                    errors[file] = {"error": "File not found in S3", "traceback": err.__traceback__}
            else:
                file_object = models.File.query.filter(
                    sqlalchemy.and_(
                        models.File.name == sqlalchemy.func.binary(file),
                        models.File.project_id == proj_in_db.id,
                    )
                ).first()
                if file_object:
                    errors[file] = {"error": "File already in database."}
                else:
                    new_file = models.File(
                        name=file,
                        name_in_bucket=vals["path_remote"],
                        subpath=vals["subpath"],
                        project_id=proj_in_db.id,
                        size_original=vals["size_raw"],
                        size_stored=vals["size_processed"],
                        compressed=not vals["compressed"],
                        public_key=vals["public_key"],
                        salt=vals["salt"],
                        checksum=vals["checksum"],
                    )
                    new_version = models.Version(
                        size_stored=new_file.size_stored, time_uploaded=datetime.datetime.utcnow()
                    )
                    proj_in_db.file_versions.append(new_version)
                    proj_in_db.files.append(new_file)
                    new_file.versions.append(new_version)

                    db.session.add(new_file)
                    files_added.append(new_file)
                db.session.commit()

        flask.current_app.logger.info(f"Files added: {files_added}")
        flask.current_app.logger.info(f"Errors while adding files: {errors}")


@click.command("lost-files")
@click.argument("action_type", type=click.Choice(["find", "list", "delete", "add-missing-buckets"]))
@flask.cli.with_appcontext
def lost_files_s3_db(action_type: str):
    """Identify (and optionally delete) files that are present in S3 or in the db, but not both.

    Args:
        action_type (str): "find", "list", or "delete"
    """
    from dds_web.database import models
    import boto3
    from dds_web.utils import bucket_is_valid

    # Interate through the units
    for unit in models.Unit.query:
        session = boto3.session.Session()

        # Connect to S3
        resource = session.resource(
            service_name="s3",
            endpoint_url=unit.safespring_endpoint,
            aws_access_key_id=unit.safespring_access,
            aws_secret_access_key=unit.safespring_secret,
        )

        # Variables
        db_count = 0  # Files not found in s3
        s3_count = 0  # Files not found in db

        # Iterate through unit projects
        for project in unit.projects:
            # Check for objects in bucket
            try:
                s3_filenames = set(
                    entry.key for entry in resource.Bucket(project.bucket).objects.all()
                )
            except resource.meta.client.exceptions.NoSuchBucket:
                if project.is_active:
                    flask.current_app.logger.warning("Missing bucket %s", project.bucket)
                    # Create a missing bucket if argument chosen
                    if action_type == "add-missing-buckets":
                        valid, message = bucket_is_valid(bucket_name=project.bucket)
                        if not valid:
                            flask.current_app.logger.warning(
                                f"Could not create bucket '{project.bucket}' for project '{project.public_id}': {message}"
                            )
                        else:
                            resource.create_bucket(Bucket=project.bucket)
                            flask.current_app.logger.info(f"Bucket '{project.bucket}' created.")
                continue

            # Get objects in project
            try:
                db_filenames = set(entry.name_in_bucket for entry in project.files)
            except sqlalchemy.exc.OperationalError:
                flask.current_app.logger.critical("Unable to connect to db")

            # Differences
            diff_db = db_filenames.difference(s3_filenames)  # In db but not in S3
            diff_s3 = s3_filenames.difference(db_filenames)  # In S3 but not in db

            # List all files which are missing in either db of s3
            # or delete the files from the s3 if missing in db, or db if missing in s3
            if action_type == "list":
                for file_entry in diff_db:
                    flask.current_app.logger.info(
                        "Entry %s (%s, %s) not found in S3", file_entry, project, unit
                    )
                for file_entry in diff_s3:
                    flask.current_app.logger.info(
                        "Entry %s (%s, %s) not found in database", file_entry, project, unit
                    )
            elif action_type == "delete":
                # s3 can only delete 1000 objects per request
                batch_size = 1000
                s3_to_delete = list(diff_s3)
                for i in range(0, len(s3_to_delete), batch_size):
                    resource.meta.client.delete_objects(
                        Bucket=project.bucket,
                        Delete={
                            "Objects": [
                                {"Key": entry} for entry in s3_to_delete[i : i + batch_size]
                            ]
                        },
                    )

                db_entries = models.File.query.filter(
                    sqlalchemy.and_(
                        models.File.name_in_bucket.in_(diff_db),
                        models.File.project_id == project.id,
                    )
                )
                for db_entry in db_entries:
                    try:
                        for db_entry_version in db_entry.versions:
                            if db_entry_version.time_deleted is None:
                                db_entry_version.time_deleted = datetime.datetime.utcnow()
                        db.session.delete(db_entry)
                        db.session.commit()
                    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError):
                        db.session.rollback()
                        flask.current_app.logger.critical("Unable to delete the database entries")
                        sys.exit(1)

            # update the counters at the end of the loop to have accurate numbers for delete
            s3_count += len(diff_s3)
            db_count += len(diff_db)

    # Print out information about actions performed in cronjob
    if s3_count or db_count:
        action_word = (
            "Found" if action_type in ("find", "list", "add-missing-buckets") else "Deleted"
        )
        flask.current_app.logger.info(
            "%s %d entries for lost files (%d in db, %d in s3)",
            action_word,
            s3_count + db_count,
            db_count,
            s3_count,
        )
        if action_type in ("find", "list", "add-missing-buckets"):
            sys.exit(1)

    else:
        flask.current_app.logger.info("Found no lost files")


@click.command("set-available-to-expired")
@flask.cli.with_appcontext
def set_available_to_expired():

    """Search for available projects whose deadlines are past and expire them"""
    flask.current_app.logger.info("Task: Checking for Expiring projects.")

    # Imports
    # Installed
    import sqlalchemy

    # Own
    from dds_web import db
    from dds_web.database import models
    from dds_web.errors import DatabaseError
    from dds_web.api.project import ProjectStatus
    from dds_web.utils import current_time, page_query

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
                    flask.current_app.logger.debug("Handling expiring project")
                    flask.current_app.logger.debug(
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
                        flask.current_app.logger.debug(
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
                    flask.current_app.logger.debug(
                        "Nothing to do for Project: %s", project.public_id
                    )
    except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.SQLAlchemyError) as err:
        flask.current_app.logger.exception(err)
        db.session.rollback()
        raise

    for unit, projects in errors.items():
        if projects:
            flask.current_app.logger.error(
                f"Following projects of Unit '{unit}' encountered issues during expiration process:"
            )
            for proj in errors[unit].keys():
                flask.current_app.logger.error(f"Error for project '{proj}': {errors[unit][proj]} ")


@click.command("set-expired-to-archived")
@flask.cli.with_appcontext
def set_expired_to_archived():
    """Search for expired projects whose deadlines are past and archive them"""

    flask.current_app.logger.debug("Task: Checking for projects to archive.")

    # Imports
    # Installed
    import sqlalchemy

    # Own
    from dds_web import db
    from dds_web.database import models
    from dds_web.errors import DatabaseError
    from dds_web.utils import current_time, page_query
    from dds_web.api.project import ProjectStatus

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
                    flask.current_app.logger.debug("Handling project to archive")
                    flask.current_app.logger.debug(
                        "Project: %s has status %s and expired on: %s",
                        project.public_id,
                        project.current_status,
                        project.current_deadline,
                    )
                    new_status_row, delete_message = archive.archive_project(
                        project=project,
                        current_time=current_time(),
                    )
                    flask.current_app.logger.debug(delete_message.strip())
                    project.project_statuses.append(new_status_row)

                    try:
                        db.session.commit()
                        flask.current_app.logger.debug(
                            "Project: %s has status Archived now!", project.public_id
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
                    flask.current_app.logger.debug(
                        "Nothing to do for Project: %s", project.public_id
                    )
    except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.SQLAlchemyError) as err:
        flask.current_app.logger.exception(err)
        db.session.rollback()
        raise

    for unit, projects in errors.items():
        if projects:
            flask.current_app.logger.error(
                f"Following projects of Unit '{unit}' encountered issues during archival process:"
            )
            for proj in errors[unit].keys():
                flask.current_app.logger.error(f"Error for project '{proj}': {errors[unit][proj]} ")


@click.command("delete-invites")
@flask.cli.with_appcontext
def delete_invites():
    """Delete invites older than a week"""

    flask.current_app.logger.debug("Task: Checking for invites to delete.")

    # Imports
    # Installed
    from datetime import datetime, timedelta
    from sqlalchemy.exc import OperationalError, SQLAlchemyError

    # Own
    from dds_web import db
    from dds_web.database import models
    from dds_web.errors import DatabaseError
    from dds_web.utils import current_time

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
                        flask.current_app.logger.warning(
                            "Invite with created_at = 0000-00-00 00:00:00 deleted."
                        )
                    else:
                        flask.current_app.logger.debug("Invite deleted.")
                except (OperationalError, SQLAlchemyError) as err:
                    errors[invite] = str(err)
                    flask.current_app.logger.exception(err)
                    db.session.rollback()
                    continue
    except (OperationalError, SQLAlchemyError) as err:
        flask.current_app.logger.exception(err)
        raise

    for invite, error in errors.items():
        flask.current_app.logger.error(f"{invite} not deleted: {error}")


@click.command("quartely-usage")
@flask.cli.with_appcontext
def quarterly_usage():
    """Get the monthly usage for the units"""

    flask.current_app.logger.debug("Task: Collecting usage information from database.")

    # Imports
    # Installed
    import sqlalchemy

    # Own
    from dds_web import db
    from dds_web.database import models
    from dds_web.utils import (
        current_time,
        page_query,
        # calculate_period_usage,
        calculate_version_period_usage,
    )

    try:
        # 1. Get projects where is_active = False
        # .. a. Check if the versions are all time_deleted == time_invoiced
        # .. b. Yes --> Set new column to True ("done")
        flask.current_app.logger.info("Marking projects as 'done'....")
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
            flask.current_app.logger.info(
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


@click.command("reporting-units-and-users")
@flask.cli.with_appcontext
def reporting_units_and_users():
    """At the start of every month, get number of units and users."""
    # Imports
    # # Installed
    import csv
    import flask_mail
    import flask_sqlalchemy
    import pathlib

    # Own
    from dds_web import errors, utils
    from dds_web.database.models import User, Unit

    # Get current date
    current_date: str = utils.timestamp(ts_format="%Y-%m-%d")

    # Location of reporting file
    reporting_file: pathlib.Path = pathlib.Path("/code/doc/reporting/dds-reporting.csv")

    # Error default
    error: str = None

    # Get email address
    recipient: str = flask.current_app.config.get("MAIL_DDS")
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
