import flask_apscheduler
import flask

## Apscheduler
scheduler = flask_apscheduler.APScheduler()


# @scheduler.task("cron", id="available_to_expired", minute=5, hour=2, misfire_grace_time=1)
@scheduler.task("interval", id="available_to_expired", seconds=10, misfire_grace_time=1)
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

        for unit in models.Unit.query.all():
            errors[unit.name] = {}

            days_in_expired = unit.days_in_expired

            for project in page_query(
                models.Project.query.filter(
                    sqlalchemy.and_(
                        models.Project.is_active == 1, models.Project.unit_id == unit.id
                    )
                )
            ):

                if (
                    project.current_status == "Available"
                    and project.current_deadline >= current_time()
                ):
                    scheduler.app.logger.debug("Handling expiring project")
                    scheduler.app.logger.debug(
                        "Project: %s has status %s and expires on: %s",
                        project.id,
                        project.current_status,
                        project.current_deadline,
                    )
                    new_status_row = expire.expire_project(
                        project=project, current_time=current_time(), deadline_in=days_in_expired
                    )

                    project.project_statuses.append(new_status_row)

                    try:
                        db.session.commit()
                        scheduler.app.logger.debug(
                            "Project: %s has status Archived now!", project.public_id
                        )
                    except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.SQLAlchemyError) as err:
                        flask.current_app.logger.exception(err)
                        db.session.rollback()
                        errors[unit.name][project.public_id] = str(err)
                    continue
                else:
                    scheduler.app.logger.debug("Nothing to do for Project: %s", project.public_id)

        for unit, projects in errors.items():
            if projects:
                scheduler.app.logger.error(
                    f"Following projects of Unit '{unit}' encountered issues during expiration process:"
                )
                for proj in errors[unit].keys():
                    scheduler.app.logger.error(f"Error for project '{proj}': {errors[unit][proj]} ")
