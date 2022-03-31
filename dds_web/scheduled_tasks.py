import flask_apscheduler
import flask

## Apscheduler
scheduler = flask_apscheduler.APScheduler()


@scheduler.task("interval", id="available_to_expired", seconds=5, misfire_grace_time=1)
def set_available_to_expired():
    scheduler.app.logger.debug("Task: Checking for Expiring projects.")
    import sqlalchemy

    from dds_web import db
    from dds_web.database import models
    from dds_web.errors import DatabaseError
    from dds_web.api.project import ProjectStatus

    from dds_web.utils import current_time, page_query

    with scheduler.app.app_context():

        for project in page_query(
            models.Project.query.filter(models.Project.is_active == 1)
        ):
      
            if "Available" in project.current_status and project.current_deadline <= current_time():
                scheduler.app.logger.debug("Handling expiring project")
                scheduler.app.logger.debug(
                    "Project: %s has status %s and expires on: %s",
                    project.id,
                    project.current_status,
                    project.current_deadline,
                )
                expire = ProjectStatus()
                new_status_row = expire.expire_project(
                    project=project, current_time=current_time(), deadline_in=30
                )

                project.project_statuses.append(new_status_row)

                try:
                    db.session.commit()
                except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.SQLAlchemyError) as err:
                    flask.current_app.logger.exception(err)
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
                scheduler.app.logger.debug("Project: %s has status Archived now!", project.title)
            else:
                scheduler.app.logger.debug("Nothing to do for Project: %s", project.title)