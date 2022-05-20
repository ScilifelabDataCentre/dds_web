from datetime import datetime, timedelta

import flask_apscheduler
import flask

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


@scheduler.task("cron", id="expired_to_archived", hour=0, minute=1, misfire_grace_time=3600)
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


# @scheduler.task("cron", id="get_monthly_usage", day='1', hour=0, minute=1)
@scheduler.task("interval", id="monthly_usage", seconds=15, misfire_grace_time=1)
def monthly_usage():
    """Get the monthly usage for the units"""

    scheduler.app.logger.debug("Task: Collecting monthly usage information from Safespring.")
    import sqlalchemy

    from dds_web import db
    from dds_web.database import models
    from dds_web.api.project import UserProjects
    from dds_web.utils import page_query

    with scheduler.app.app_context():
        # a mock dict with data that should be obtained from Safesprig's API
        safespring_data = {}
        for unit in db.session.query(models.Unit).all():
            safespring_data[unit.safespring_name] = {
                "TotalBytes": 434595434499,
                "TotalBytesRounded": 1434614451200,
                "TotalEntries": 10333,
            }

        for safespring_project, usage_info in safespring_data.items():
            usage = f"Total usage for unit {unit.name} ({safespring_project}): {usage_info['TotalBytes']}"
            scheduler.app.logger.info(usage)

        scheduler.app.logger.debug("Task: Projects usage from database")
        try:
            for unit in db.session.query(models.Unit).with_for_update().all():
                scheduler.app.logger.debug(f"Projects in unit {unit.safespring_name}")
                for project in page_query(
                    db.session.query(models.Project)
                    .filter(
                        sqlalchemy.and_(
                            models.Project.is_active == 1, models.Project.unit_id == unit.id
                        )
                    )
                    .with_for_update()
                ):
                    proj_bhours, proj_cost = UserProjects.project_usage(project)
                    scheduler.app.logger.info(
                        "Current total usage for project %s is %s bhours, and total cost is %s kr",
                        project.public_id,
                        proj_bhours,
                        proj_cost,
                    )
        except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.SQLAlchemyError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise
