import flask_apscheduler
import flask

## Apscheduler
scheduler = flask_apscheduler.APScheduler()


@scheduler.task("interval", id="available_to_expired", seconds=5, misfire_grace_time=1)
def change_status_to_expired():
    # print("Task: Change project status from Available to expired.", flush=True)
    from dds_web.database import models

    from dds_web.utils import current_time, page_query

    with scheduler.app.app_context():
        scheduler.app.logger.debug("This means that the app context works!")
        # test = models.Project.query.all()
        # print(test, flush=True)

        for project in page_query(
            # models.ProjectStatuses.query.filter(models.ProjectStatuses.is_active >= current_time())
            models.Project.query.filter(models.Project.is_active == 1)
        ):
            if "Available" in project.current_status:
                scheduler.app.logger.debug("Project: %s has status %s - Expires: %s", project.title, project.current_status, project.current_deadline)
                # scheduler.app.logger.debug(project.id)
                # scheduler.app.logger.debug(project.current_deadline)
            
