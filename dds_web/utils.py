"Utility functions and classes useful within the DDS."

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import datetime
import os
import pathlib

# Installed
import pandas
from contextlib import contextmanager
import flask
import sqlalchemy

# # imports related to scheduling
import atexit
import werkzeug
from apscheduler.schedulers import background

# Own modules
from dds_web.database import models
from dds_web import db, C_TZ


####################################################################################################
# FUNCTIONS ############################################################################ FUNCTIONS #
####################################################################################################


def timestamp(dts=None, datetime_string=None, ts_format="%Y-%m-%d %H:%M:%S.%f%z"):
    """Gets the current time. Formats timestamp.

    Returns:
        str:    Timestamp in format 'YY-MM-DD_HH-MM-SS'

    """

    if datetime_string is not None:
        datetime_stamp = datetime.datetime.strptime(datetime_string, ts_format)
        return str(datetime_stamp.date())

    now = datetime.datetime.now(tz=C_TZ) if dts is None else dts
    t_s = str(now.strftime(ts_format))
    return t_s


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


def invoice_units():
    """Get invoicing specification from Safespring, calculate and save GBHours and cost for each
    unit and project."""

    flask.current_app.logger.debug("Calculating invoicing info...")

    # Create invoice specification
    # TODO (ina): Change to Safespring API call
    parent_dir = pathlib.Path("").parent

    # From safespring
    old_file = parent_dir / pathlib.Path("development/invoicing/safespring_invoicespec.csv")

    current_time = timestamp(ts_format="%Y-%m-%d_%H-%M-%S")
    to_file = old_file
    # to_file = parent_dir / pathlib.Path(f"development/invoicing/{current_time}.csv") # TODO (ina): uncomment later

    # shutil.copy(old_file, to_file)    # TODO (ina): uncomment later

    # Get data
    csv_contents = pandas.read_csv(to_file, sep=";", header=1)

    with flask.current_app.app_context():
        try:
            all_units = models.Unit.query.all()
        except sqlalchemy.exc.SQLAlchemyError as err:
            flask.current_app.logger.warning(
                f"Failed getting unit information from database. Cannot generate invoicing information: {err}"
            )
        else:
            for f in all_units:
                # Get safespring project name
                safespring_project_row = csv_contents.loc[csv_contents["project"] == f.safespring]

                # Total number of GB hours and cost saved in the db for the specific unit
                total_gbhours_db = 0.0

                usage = {}
                for p in f.projects:
                    usage[p.public_id] = {"gbhours": 0.0, "cost": 0.0}

                    # All project file versions
                    for v in p.file_versions:

                        # Move on to next if full period already invoiced
                        if v.time_deleted and v.time_invoiced and v.time_deleted == v.time_invoiced:
                            flask.current_app.logger.debug(f"Period invoiced fully : {v}")
                            continue

                        start, end = ("", "")
                        if not v.time_invoiced:  # not included in invoice
                            flask.current_app.logger.debug(f"Invoice = NULL : {v}")
                            start = v.time_uploaded
                            end = v.time_deleted if v.time_deleted else timestamp()
                        else:  # included in invoice
                            start = v.time_invoiced
                            end = (
                                v.time_deleted
                                if v.time_deleted and v.time_deleted > v.time_invoiced
                                else timestamp()
                            )

                        # Calculate hours of the current file
                        period_start = datetime.datetime.strptime(
                            start,
                            "%Y-%m-%d %H:%M:%S.%f%z",
                        )
                        period_end = datetime.datetime.strptime(
                            end,
                            "%Y-%m-%d %H:%M:%S.%f%z",
                        )
                        file_hours = (period_end - period_start).seconds / (60 * 60)
                        # Calculate GBHours, if statement to avoid zerodivision exception
                        gb_hours = ((v.size_stored / 1e9) / file_hours) if file_hours else 0.0

                        # Save file version gbhours to project info and increase total unit sum
                        usage[p.public_id]["gbhours"] += gb_hours
                        total_gbhours_db += gb_hours

                        v.time_invoiced = end
                        db.session.commit()

                for proj, vals in usage.items():
                    gbhour_perc = (
                        (vals["gbhours"] / total_gbhours_db)
                        if 0.0 not in [vals["gbhours"], total_gbhours_db]
                        else 0.0
                    )

                    usage[proj]["cost"] = safespring_project_row.subtotal.values[0] * gbhour_perc

                # Maybe uncomment later - saves calculated info to json file
                # new_file = parent_dir / pathlib.Path(
                #     f"development/invoicing/{f.id}_{current_time}.json"
                # )
                # with new_file.open(mode="w") as file:
                #     json.dump(usage, file)


def remove_invoiced():
    """Clean up in the Version table. Those rows which have an active file will not be deleted,
    neither will the rows which have hours not included in previous invoices."""

    flask.current_app.logger.debug("Removing deleted and invoiced versions...")

    with flask.current_app.app_context():
        try:
            # Get all rows in version table
            # TODO (ina, senthil): change to better method for when huge number of rows
            all_versions = models.Version.query.all()
        except sqlalchemy.exc.SQLAlchemyError as err:
            # TODO (ina, senthil): Something else should happen here
            flask.current_app.logger.warning(
                f"Failed getting verions from database. Cannot remove invoiced rows: {err}"
            )
        else:
            for v in all_versions:
                # Delete those rows which corresponding file has been deleted and which
                # have been fully invoiced - no more costs for the version after deletion,
                # if the file was deleted more than 30 days ago
                if v.time_deleted and v.time_invoiced and v.time_deleted == v.time_invoiced:
                    deleted = datetime.datetime.strptime(
                        v.time_deleted,
                        "%Y-%m-%d %H:%M:%S.%f%z",
                    )
                    now = datetime.datetime.strptime(
                        timestamp(),
                        "%Y-%m-%d %H:%M:%S.%f%z",
                    )
                    diff = now - deleted
                    if diff.seconds > 60:  # TODO (ina): Change to correct interval -- 30 days?
                        flask.current_app.logger.debug(f"Deleting: {v}")
                        db.session.delete(v)
                        db.session.commit()


def remove_expired():
    """Clean up in File table -- those which have been stored in the system for too long are moved to the DeletedFile table."""

    flask.current_app.logger.debug("Cleaning up File table...")

    # TODO (ina, senthil): Delete from bucket, change this to check everyday, get files which have expired by getting current time, and days_to_expire from unit info - unique times to expire the files for each unit.
    with flask.current_app.app_context():
        try:
            # Get all rows in version table
            for file in page_query(
                models.File.query.filter(models.File.expires <= datetime.datetime.now(tz=C_TZ))
            ):

                flask.current_app.logger.debug("File: %s - Expires: %s", file, file.expires)

                new_expired = models.ExpiredFile(
                    public_id=file.public_id,
                    name=file.name,
                    name_in_bucket=file.name_in_bucket,
                    subpath=file.subpath,
                    size_original=file.size_original,
                    size_stored=file.size_stored,
                    compressed=file.compressed,
                    public_key=file.public_key,
                    salt=file.salt,
                    checksum=file.checksum,
                    time_latest_download=file.time_latest_download,
                    project_id=file.project_id,
                )

                db.session.add(new_expired)

                db.session.delete(file)
                db.session.commit()

        except sqlalchemy.exc.SQLAlchemyError as err:
            # TODO (ina, senthil): Something else should happen here
            flask.current_app.logger.warning(f"test: {err}")


def permanent_delete():
    """Permanently delete the files in expired files table."""

    # TODO (ina, senthil): Check which rows have been stored in the ExpiredFile table for more than a month, delete them from S3 bucket and table.

    flask.current_app.logger.debug(
        "Permanently deleting the expired files (not implemented atm, just scheduled function)"
    )


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
    flask.current_app.logger.info("Initiated main scheduler")

    # Schedule invoicing calculations every 30 days
    # TODO (ina): Change to correct interval - 30 days
    if not scheduler.get_job("calc_costs"):
        flask.current_app.logger.info("Added job: calc_costs")
        scheduler.add_job(
            invoice_units,
            "cron",
            id="calc_costs",
            replace_existing=False,
            coalesce=True,  # when several run times are due, none the less run the rob only once
            month="1-12",
            day="1-31",
            hour="0",
        )

    # Schedule delete of rows in version table after a specific amount of time
    # Currently: First of every month
    if not scheduler.get_job("remove_versions"):
        flask.current_app.logger.info("Added job: remove_versions")
        scheduler.add_job(
            remove_invoiced,
            "cron",
            id="remove_versions",
            replace_existing=False,
            coalesce=True,  # when several run times are due, none the less run the rob only once
            month="1-12",
            day="1",
            hour="1",
        )

    # Schedule move of rows in files table after a specific amount of time
    # to DeletedFiles (does not exist yet) table
    # Currently: First of every month
    if not scheduler.get_job("remove_expired"):
        flask.current_app.logger.info("Added job: remove_expired")
        scheduler.add_job(
            remove_expired,
            "cron",
            id="remove_expired",
            replace_existing=False,
            coalesce=True,
            month="1-12",
            day="1",
            hour="2",
        )

    # Schedule delete rows in expiredfiles table after a specific amount of time
    # TODO (ina): Change interval - 1 day?
    if not scheduler.get_job("permanent_delete"):
        flask.current_app.logger.info("Added job: permanent_delete")
        scheduler.add_job(
            permanent_delete,
            "cron",
            id="permanent_delete",
            replace_existing=False,
            coalesce=True,
            month="1-12",
            day="1-31",
            hour="3",
        )

    scheduler.start()
    flask.current_app.logger.info("Started main scheduler")

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

    # Print the currently scheduled jobs as verification:
    joblist = scheduler.get_jobs()
    flask.current_app.logger.info("Currently scheduled jobs:")
    for job in joblist:
        flask.current_app.logger.info(f"Job: {job}")
