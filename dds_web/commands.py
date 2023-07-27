"""Flask commands runable in container."""

# Imports

# Standard
import os
import re
import sys
import datetime
from dateutil.relativedelta import relativedelta
import gc

# Installed
import click
import flask
import flask_mail
import sqlalchemy
import botocore

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
@click.option("--quota", "-q", type=int, required=True)
@click.option("--warn-at", "-w", type=int, required=False, default=80)
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
    quota,
    warn_at,
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
        sto4_endpoint=safespring_endpoint,
        sto4_name=safespring_name,
        sto4_access=safespring_access,
        sto4_secret=safespring_secret,
        days_in_available=days_in_available,
        days_in_expired=days_in_expired,
        quota=quota,
        warning_level=warn_at,
    )
    db.session.add(new_unit)
    db.session.commit()

    flask.current_app.logger.info(f"Unit '{name}' created")

    del safespring_endpoint
    del safespring_name
    del safespring_access
    del safespring_secret
    gc.collect()

@click.command("update-unit")
@click.option("--unit-id", "-p", type=str, required=True)
@click.option("--sto4-endpoint", "-se", type=str, required=True)
@click.option("--sto4-name", "-sn", type=str, required=True)
@click.option("--sto4-access", "-sa", type=str, required=True)
@click.option("--sto4-secret", "-ss", type=str, required=True)
@flask.cli.with_appcontext
def update_unit(unit_id, sto4_endpoint, sto4_name, sto4_access, sto4_secret):
    """Update unit info."""
    # Imports
    import rich.prompt
    from dds_web import db
    from dds_web.utils import current_time
    from dds_web.database import models

    # Get unit
    unit: models.Unit = models.Unit.query.filter_by(public_id=unit_id).one_or_none()
    if not unit:
        flask.current_app.logger.error(f"There is no unit with the public ID '{unit_id}'.")
        return

    # Warn user if sto4 info already exists
    if unit.sto4_start_time:
        do_update = rich.prompt.Confirm.ask(
            f"Unit '{unit_id}' appears to have sto4 variables set already. Are you sure you want to overwrite them?"
        )
        if not do_update:
            flask.current_app.logger.info(f"Cancelling sto4 update for unit '{unit_id}'.")
            return

    # Set sto4 info
    unit.sto4_start_time = current_time()
    unit.sto4_endpoint = sto4_endpoint
    unit.sto4_name = sto4_name
    unit.sto4_access = sto4_access
    unit.sto4_secret = sto4_secret
    db.session.commit()

    flask.current_app.logger.info(f"Unit '{unit_id}' updated successfully")

    del sto4_endpoint
    del sto4_name
    del sto4_access
    del sto4_secret
    gc.collect()


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


@click.group(name="lost-files")
@flask.cli.with_appcontext
def lost_files_s3_db():
    """Group command for handling lost files: Either in db or s3, but not in both."""
    pass


@lost_files_s3_db.command(name="ls")
@click.option("--project-id", "-p", type=str, required=False)
@flask.cli.with_appcontext
def list_lost_files(project_id: str):
    """List lost files: Existing either in DB or S3, not in both."""
    # Imports
    import boto3
    from dds_web.database import models
    from dds_web.utils import list_lost_files_in_project

    if project_id:
        flask.current_app.logger.debug(f"Searching for lost files in project '{project_id}'.")
        # Get project if option used
        project: models.Project = models.Project.query.filter_by(public_id=project_id).one_or_none()
        if not project:
            flask.current_app.logger.error(f"No such project: '{project_id}'")
            sys.exit(1)

        # Start s3 session
        session = boto3.session.Session()

        # Check which Safespring storage location to use
        # Use sto2 as default
        endpoint_url = project.responsible_unit.sto2_endpoint
        aws_access_key_id = project.responsible_unit.sto2_access
        aws_secret_access_key = project.responsible_unit.sto2_secret

        # Use sto4 if project created after sto4 info added
        sto4_endpoint_added = project.responsible_unit.sto4_start_time
        if sto4_endpoint_added and project.date_created > sto4_endpoint_added:
            endpoint_url = project.responsible_unit.sto4_endpoint
            aws_access_key_id = project.responsible_unit.sto4_access
            aws_secret_access_key = project.responsible_unit.sto4_secret

        # Connect to S3
        resource = session.resource(
            service_name="s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        # List the lost files
        try:
            in_db_but_not_in_s3, in_s3_but_not_in_db = list_lost_files_in_project(
                project=project, s3_resource=resource
            )
        except (botocore.exceptions.ClientError, sqlalchemy.exc.OperationalError):
            flask.current_app.logger.info("Not listing files due to error above.")
            sys.exit(1)

        # Number of lost files listed
        num_lost_files: int = sum([len(in_db_but_not_in_s3), len(in_s3_but_not_in_db)])

        # Print out message if no lost files
        if not num_lost_files:
            flask.current_app.logger.info(f"No lost files in project '{project_id}'")

        flask.current_app.logger.info(
            f"Lost files in project: {project_id}\t"
            f"\tIn DB but not S3: {len(in_db_but_not_in_s3)}\t"
            f"In S3 but not DB: {len(in_s3_but_not_in_db)}\n"
        )
    else:
        flask.current_app.logger.debug(
            "No project specified, searching for lost files in all units."
        )

        # Interate through the units
        for unit in models.Unit.query:
            flask.current_app.logger.info(f"Listing lost files in unit: {unit.public_id}")

            num_proj_errors: int = 0

            # Start s3 session
            session = boto3.session.Session()

            # Connect to S3
            resource_unit = session.resource(
                service_name="s3",
                endpoint_url=unit.sto2_endpoint,
                aws_access_key_id=unit.sto2_access,
                aws_secret_access_key=unit.sto2_secret,
            )

            # Counts
            in_db_but_not_in_s3_count: int = 0
            in_s3_but_not_in_db_count: int = 0

            # List files in all projects
            for proj in unit.projects:
                # List the lost files
                try:
                    in_db_but_not_in_s3, in_s3_but_not_in_db = list_lost_files_in_project(
                        project=proj, s3_resource=resource_unit
                    )
                except (botocore.exceptions.ClientError, sqlalchemy.exc.OperationalError):
                    num_proj_errors += 1
                    continue

                # Add to sum
                in_db_but_not_in_s3_count += len(in_db_but_not_in_s3)
                in_s3_but_not_in_db_count += len(in_s3_but_not_in_db)

            if not sum([in_db_but_not_in_s3_count, in_s3_but_not_in_db_count]):
                flask.current_app.logger.info(f"No lost files for unit '{unit.public_id}'")

            flask.current_app.logger.info(
                f"Lost files for unit: {unit.public_id}\t"
                f"\tIn DB but not S3: {in_db_but_not_in_s3_count}\t"
                f"In S3 but not DB: {in_s3_but_not_in_db_count}\t"
                f"Project errors: {num_proj_errors}\n"
            )


@lost_files_s3_db.command(name="add-missing-bucket")
@click.option("--project-id", "-p", type=str, required=True)
@flask.cli.with_appcontext
def add_missing_bucket(project_id: str):
    """Add project bucket if project is active and bucket is missing."""
    # Imports
    import boto3
    from botocore.client import ClientError
    from dds_web.database import models
    from dds_web.utils import bucket_is_valid

    # Get project object
    project: models.Project = models.Project.query.filter_by(public_id=project_id).one_or_none()
    if not project:
        flask.current_app.logger.error(f"No such project: '{project_id}'")
        sys.exit(1)

    # Only create new bucket if project is active
    if not project.is_active:
        flask.current_app.logger.error(f"Project '{project_id}' is not an active project.")
        sys.exit(1)

    # Start s3 session
    session = boto3.session.Session()

    # Connect to S3
    resource = session.resource(
        service_name="s3",
        endpoint_url=project.responsible_unit.sto2_endpoint,
        aws_access_key_id=project.responsible_unit.sto2_access,
        aws_secret_access_key=project.responsible_unit.sto2_secret,
    )

    # Check if bucket exists
    try:
        resource.meta.client.head_bucket(Bucket=project.bucket)
    except ClientError:
        flask.current_app.logger.info("Project bucket is missing. Proceeding...")

        # Verify that bucket name is valid and if so create bucket
        valid, message = bucket_is_valid(bucket_name=project.bucket)
        if not valid:
            flask.current_app.logger.warning(
                f"Invalid bucket name: '{project.bucket}'. Details: {message}. Bucket not created."
            )
            sys.exit(1)
        else:
            resource.create_bucket(Bucket=project.bucket)
            flask.current_app.logger.info(f"Bucket '{project.bucket}' created.")
    else:
        flask.current_app.logger.info(
            f"Bucket for project '{project.public_id}' found; Bucket not missing. Will not create bucket."
        )


@lost_files_s3_db.command(name="delete")
@click.option("--project-id", "-p", type=str, required=True)
@flask.cli.with_appcontext
def delete_lost_files(project_id: str):
    """Delete files that are located in only s3 or db."""
    # Imports
    import boto3
    from dds_web.database import models
    from dds_web.utils import list_lost_files_in_project

    # Get project object
    project: models.Project = models.Project.query.filter_by(public_id=project_id).one_or_none()
    if not project:
        flask.current_app.logger.error(f"No such project: '{project_id}'")
        sys.exit(1)

    # Start s3 session
    session = boto3.session.Session()

    # Connect to S3
    resource = session.resource(
        service_name="s3",
        endpoint_url=project.responsible_unit.sto2_endpoint,
        aws_access_key_id=project.responsible_unit.sto2_access,
        aws_secret_access_key=project.responsible_unit.sto2_secret,
    )

    # Get list of lost files
    in_db_but_not_in_s3, in_s3_but_not_in_db = list_lost_files_in_project(
        project=project, s3_resource=resource
    )

    # S3 can only delete 1000 objects per request
    batch_size = 1000
    s3_to_delete = list(in_s3_but_not_in_db)

    # Delete items from S3
    for i in range(0, len(s3_to_delete), batch_size):
        resource.meta.client.delete_objects(
            Bucket=project.bucket,
            Delete={"Objects": [{"Key": entry} for entry in s3_to_delete[i : i + batch_size]]},
        )

    # Delete items from DB
    db_entries = models.File.query.filter(
        sqlalchemy.and_(
            models.File.name_in_bucket.in_(in_db_but_not_in_s3),
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

    flask.current_app.logger.info(f"Files deleted from S3: {len(in_s3_but_not_in_db)}")
    flask.current_app.logger.info(f"Files deleted from DB: {len(in_db_but_not_in_s3)}")


@click.command("set-available-to-expired")
@flask.cli.with_appcontext
def set_available_to_expired():
    """
    Search for available projects whose deadlines are past and expire them.
    Should be run every day at around 00:01.
    """

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
    """
    Search for expired projects whose deadlines are past and archive them.
    Should be run every day at around 01:01.
    """

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
    """
    Delete invites older than a week.
    Should be run evry day at around 00:01.
    """

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
        any_deleted: bool = False
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
                        flask.current_app.logger.debug(
                            f"Invite deleted: {invite.email} (created at {invite.created_at})."
                        )
                    any_deleted = True
                except (OperationalError, SQLAlchemyError) as err:
                    errors[invite] = str(err)
                    flask.current_app.logger.exception(err)
                    db.session.rollback()
                    continue
        if not any_deleted:
            flask.current_app.logger.info("No invites for deletion.")
    except (OperationalError, SQLAlchemyError) as err:
        flask.current_app.logger.exception(err)
        raise

    for invite, error in errors.items():
        flask.current_app.logger.error(f"{invite} not deleted: {error}")


@click.command("quartely-usage")
@flask.cli.with_appcontext
def quarterly_usage():
    """
    Get the monthly usage for the units
    Should be run on the 1st of Jan,Apr,Jul,Oct at around 00:01.
    """

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


@click.command("stats")
@flask.cli.with_appcontext
def collect_stats():
    """
    At the start of every month, get number of units and users.
    Should be run on the 1st of each month, at around 00:01.
    """
    # Imports
    # Installed
    import flask_mail
    from sqlalchemy.sql import func

    # Own
    import dds_web.utils
    from dds_web.utils import bytehours_in_last_month, page_query, calculate_bytehours
    from dds_web.database.models import (
        Unit,
        UnitUser,
        ResearchUser,
        SuperAdmin,
        User,
        Reporting,
        Project,
        ProjectUsers,
        Version,
    )

    # Get current time
    current_time = dds_web.utils.timestamp(ts_format="%Y-%m-%d")

    # Get email address
    recipient: str = flask.current_app.config.get("MAIL_DDS")
    error_subject: str = "[CRONJOB] Error during collection of DDS unit- and user statistics."
    error_body: str = (
        f"The cronjob 'reporting' experienced issues. Please see logs. Time: {current_time}."
    )

    # New reporting row - numbers are automatically set
    try:
        # User stats
        researcher_count = ResearchUser.query.count()
        unit_personnel_count = UnitUser.query.filter_by(is_admin=False).count()
        unit_admin_count = UnitUser.query.filter_by(is_admin=True).count()
        superadmin_count = SuperAdmin.query.count()
        total_user_count = User.query.count()

        # Unique project owners
        project_owner_unique_count: int = (
            ProjectUsers.query.filter_by(owner=True)
            .with_entities(ProjectUsers.user_id)
            .distinct()
            .count()
        )

        # Project count
        total_project_count = Project.query.count()
        active_project_count = Project.query.filter_by(is_active=True).count()
        inactive_project_count = Project.query.filter_by(is_active=False).count()

        # Unit count
        unit_count = Unit.query.count()

        # Amount of data
        # Currently stored
        bytes_stored_now: int = sum(proj.size for proj in Project.query.filter_by(is_active=True))
        tb_stored_now: float = round(bytes_stored_now / 1e12, 2)
        # Uploaded since start
        bytes_uploaded_since_start = db.session.query(
            func.sum(Version.size_stored).label("sum_bytes")
        ).first()
        tb_uploaded_since_start: float = round(int(bytes_uploaded_since_start.sum_bytes) / 1e12, 2)

        # TBHours
        # In last month
        byte_hours_sum = sum(
            bytehours_in_last_month(version=version)
            for version in page_query(Version.query)
            if version.time_deleted is None
            or version.time_deleted > (dds_web.utils.current_time() - relativedelta(months=1))
        )
        tbhours = round(byte_hours_sum / 1e12, 2)
        # Since start
        time_now = dds_web.utils.current_time()
        byte_hours_sum_total = sum(
            calculate_bytehours(
                minuend=version.time_deleted or time_now,
                subtrahend=version.time_uploaded,
                size_bytes=version.size_stored,
            )
            for version in page_query(Version.query)
        )
        tbhours_total = round(byte_hours_sum_total / 1e12, 2)

        # Add to database
        new_reporting_row = Reporting(
            unit_count=unit_count,
            researcher_count=researcher_count,
            unit_personnel_count=unit_personnel_count,
            unit_admin_count=unit_admin_count,
            superadmin_count=superadmin_count,
            total_user_count=total_user_count,
            project_owner_unique_count=project_owner_unique_count,
            total_project_count=total_project_count,
            active_project_count=active_project_count,
            inactive_project_count=inactive_project_count,
            tb_stored_now=tb_stored_now,
            tb_uploaded_since_start=tb_uploaded_since_start,
            tbhours=tbhours,
            tbhours_since_start=tbhours_total,
        )
        db.session.add(new_reporting_row)
        db.session.commit()
    except BaseException as err:  # We want to know if there's any error
        db.session.rollback()
        flask.current_app.logger.warning(
            f"Exception raised during reporting cronjob. Preparing email. Error: {err}"
        )
        # Send email about error
        file_error_msg: flask_mail.Message = flask_mail.Message(
            subject=error_subject,
            recipients=[recipient],
            body=error_body,
        )
        dds_web.utils.send_email_with_retry(msg=file_error_msg)
        raise
    else:
        flask.current_app.logger.info(
            f"Unit- and user statistis collected successfully: {current_time}"
        )


@click.command("monitor-usage")
@flask.cli.with_appcontext
def monitor_usage():
    """
    Check the units storage usage and compare with chosen quota.
    Should be run on the 1st of each month, at around 00:01.
    """
    flask.current_app.logger.info("Starting: Checking unit quotas and usage...")

    # Imports
    # Own
    from dds_web.database import models
    import dds_web.utils

    # Email settings
    recipient: str = flask.current_app.config.get("MAIL_DDS")
    default_subject: str = "DDS: Usage quota warning!"

    # Run task
    for unit in models.Unit.query:
        flask.current_app.logger.info(f"Checking quotas and usage for: {unit.name}")

        # Get info from database
        quota: int = unit.quota
        warn_after: int = unit.warning_level
        current_usage: int = unit.size

        # Check if 0 and then skip the next steps
        if not current_usage:
            flask.current_app.logger.info(
                f"{unit.name} usage: {current_usage} bytes. Skipping percentage calculation."
            )
            continue

        # Calculate percentage of quota
        perc_used_decimal = current_usage / quota
        perc_used = round(perc_used_decimal * 100, 3)

        # Information to log and potentially send
        info_string: str = (
            f"- Quota:{quota} bytes\n"
            f"- Warning level: {warn_after*quota} bytes ({warn_after*100}%)\n"
            f"- Current usage: {current_usage} bytes ({perc_used}%)\n"
        )
        flask.current_app.logger.debug(
            f"Monitoring the usage for unit '{unit.name}' showed the following:\n" + info_string
        )

        # Email if the unit is using more
        if perc_used_decimal > warn_after:
            # Email settings
            message: str = (
                "A SciLifeLab Unit is approaching the allocated data quota.\n"
                f"Affected unit: {unit.name}\n"
                f"{info_string}"
            )
            flask.current_app.logger.info(message)
            msg: flask_mail.Message = flask_mail.Message(
                subject=default_subject,
                recipients=[recipient],
                body=message,
            )
            dds_web.utils.send_email_with_retry(msg=msg)
