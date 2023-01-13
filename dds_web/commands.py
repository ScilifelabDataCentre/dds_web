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
import flask_mail
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
        safespring_endpoint=safespring_endpoint,
        safespring_name=safespring_name,
        safespring_access=safespring_access,
        safespring_secret=safespring_secret,
        days_in_available=days_in_available,
        days_in_expired=days_in_expired,
        quota=quota,
        warning_level=warn_at,
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


@click.command("monitor-usage")
@flask.cli.with_appcontext
def monitor_usage():
    """Check the units storage usage and compare with chosen quota."""
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
            flask.current_app.logger.info(f"{unit.name} usage: {current_usage} bytes. Skipping percentage calculation.")
            continue

        # Calculate percentage of quota
        perc_used = current_usage / quota
        
        # Information to log and potentially send
        info_string: str = (
            f"- Quota:{quota} bytes\n"
            f"- Warning level: {warn_after*quota} bytes ({warn_after}%)\n"
            f"- Current usage: {current_usage} bytes ({perc_used})\n"
        )
        flask.current_app.logger.debug(
            f"Monitoring the usage for unit '{unit.name}' showed the following:\n" + info_string
        )

        # Email if the unit is using more
        if perc_used > warn_after:
            # Email settings
            message: str = (
                "A SciLifeLab Unit is approaching the allocated data quota.\n"
                f"Affected unit: {unit.name}\n"
                f"{info_string}"
            )
            msg: flask_mail.Message = flask_mail.Message(
                subject=default_subject,
                recipients=[recipient],
                body=message,
            )
            dds_web.utils.send_email_with_retry(msg=msg)
