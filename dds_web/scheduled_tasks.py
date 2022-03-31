import flask_apscheduler
import flask

## Apscheduler
scheduler = flask_apscheduler.APScheduler()


@scheduler.task("interval", id="available_to_expired", seconds=5, misfire_grace_time=1)
def set_available_to_expired():
    # print("Task: Change project status from Available to expired.", flush=True)
    import sqlalchemy

    from dds_web import db
    from dds_web.database import models
    from dds_web.errors import DatabaseError
    from dds_web.api.project import ProjectStatus

    from dds_web.utils import current_time, page_query

    with scheduler.app.app_context():
        scheduler.app.logger.debug("Handling expiring projects")

        # expired_projs = (
        #     db.session.query(models.ProjectStatuses.project_id)
        #     .filter(models.ProjectStatuses.status == "Expired")
        #     .all()
        # )
        # for p in expired_projs:
        #     scheduler.app.logger.debug("Expired: %s", expired_projs)

        available_projs = db.session.query(models.Project).filter(
            models.Project.current_status == "Available"
        )

        # expiring_projs = db.session.query()

        # scheduler.app.logger.debug(type(available_projs))
        for p in available_projs:
            scheduler.app.logger.debug("Available: %s", p)

        for project in page_query(
            # for project in available_projs:
            # (
            #     # models.ProjectStatuses.query.filter(models.ProjectStatuses.is_active >= current_time())
            models.Project.query.filter(models.Project.is_active == 1)
        ):
      
            if "Available" in project.current_status and project.current_deadline >= current_time():
                scheduler.app.logger.debug(
                    "Project: %s has status %s - Expires: %s",
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
            #     change = status.expire_project(
            #         project=project, current_time=current_time, deadline_in=30
            #     )
            #     # change.query.all()
            #     scheduler.app.logger.debug(change.query.all())
            #     # status.expire_project(status="Expired", date_created=current_time, deadline=current_time)
            #     # models.ProjectStatuses.query.
            # # else:
            #     scheduler.app.logger.debug("Nothing to do for Project: %s", project.title)
