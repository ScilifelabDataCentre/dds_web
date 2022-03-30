import flask_apscheduler
import flask 

# from dds_web.database import models


# Apscheduler
scheduler = flask_apscheduler.APScheduler()

@scheduler.task("interval", id="testtask", seconds=10, misfire_grace_time=1)
def task1():
    print("task 1 executed", flush=True)
    with scheduler.app.app_context():
        scheduler.app.logger.debug("testing")
        
        # scheduler.
    #     # test = models.Projects.query.all()
    # app.logger.debug("testing")