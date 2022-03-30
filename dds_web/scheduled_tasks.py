import flask_apscheduler
import flask 

# from dds_web.database import models


# Apscheduler
scheduler = flask_apscheduler.APScheduler()

@scheduler.task("interval", id="testtask", seconds=10, misfire_grace_time=1)
def task1():
    print("task 1 executed", flush=True)
    from dds_web.database import models
    # from dds_web.utils import current_time, page_query
    with scheduler.app.app_context():
        scheduler.app.logger.debug("testing")
        test = models.Project.query.all()
        print(test, flush=True)
        # for project in page_query(
        #     models.ProjectStatuses.query.filter(models.ProjectStatuses.deadline <= current_time())
        # ):

        #     flask.current_app.logger.debug("Project: %s - Expires: %s", project, project.expires)