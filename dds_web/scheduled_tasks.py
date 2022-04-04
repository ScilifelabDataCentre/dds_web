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
                            project.id,
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
    import sqlalchemy
    from dds_web import db
    from dds_web.database import models
    from dds_web.errors import DatabaseError
    from dds_web.utils import current_time
    from dds_web.api.project import ProjectStatus

    with scheduler.app.app_context():
        archived_projs = db.session.query(models.ProjectStatuses.project_id).filter(
            models.ProjectStatuses.status == "Archived"
        )
        expired_projs = models.ProjectStatuses.query.filter(
            models.ProjectStatuses.project_id.not_in(archived_projs),
            models.ProjectStatuses.status == "Expired",
            models.ProjectStatuses.deadline <= current_time(),
        ).all()

        archive = ProjectStatus()
        for proj_status in expired_projs:
            new_status_row, delete_message = archive.archive_project(
                project=proj_status.project,
                current_time=current_time(),
            )
            proj_status.project.project_statuses.append(new_status_row)
            scheduler.app.logger.debug(delete_message)

            try:
                db.session.commit()
            except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.SQLAlchemyError) as err:
                scheduler.app.logger.exception(err)
                db.session.rollback()
                raise DatabaseError(
                    message=str(err),
                    alt_message=(
                        "Status was not updated"
                        + (
                            ": Database malfunction."
                            if isinstance(err, sqlalchemy.exc.OperationalError)
                            else ": Server Error."
                        )
                    ),
                ) from err
