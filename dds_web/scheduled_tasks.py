import flask_apscheduler
import flask

# Apscheduler
scheduler = flask_apscheduler.APScheduler()


@scheduler.task("interval", id="available_to_expired", seconds=10, misfire_grace_time=1)
def change_status_to_expired():
    # print("Task: Change project status from Available to expired.", flush=True)
    from dds_web.database import models

    # from dds_web.utils import current_time, page_query

    with scheduler.app.app_context():
        # scheduler.app.logger.debug("This means that the app context works!")
        test = models.Project.query.all()
        # print(test, flush=True)

        # for project in page_query(
        #     models.ProjectStatuses.query.filter(models.ProjectStatuses.deadline <= current_time())
        # ):

        #     flask.current_app.logger.debug("Project: %s - Expires: %s", project, project.expires)


@scheduler.task("interval", id="expired_to_archived", seconds=30, misfire_grace_time=1)
def set_expired_to_archived():
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
            models.ProjectStatuses.project_id.notin_(archived_projs),
            models.ProjectStatuses.status == "Expired",
            models.ProjectStatuses.deadline <= current_time(),
        ).all()

        archive = ProjectStatus()
        for proj_status in expired_projs:
            new_status_row = archive.expire_project(
                project=proj_status.project,
                current_time=current_time(),
            )
            proj_status.project.project_statuses.append(new_status_row)

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
