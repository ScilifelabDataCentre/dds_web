####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library

# Installed
import flask_restful
import flask
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.exceptions import NoSuchJobError

# Own modules
from dds_web import auth
from dds_web.errors import (
    InvalidJobIdError,
    DDSArgumentError,
)
from dds_web.api.dds_decorators import (
    logging_bind_request,
    json_required,
    handle_validation_errors,
)

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class JobInfo(flask_restful.Resource):
    """Gets the status of a given job in the Redis Queue"""

    @auth.login_required
    @logging_bind_request
    def get(self):
        """Get the status of a given job in the Redis Queue"""
        job_id = flask.request.args.get("job_id")
        if job_id is None:
            raise DDSArgumentError(message="No job_id provided")

        # Get redis connection and queue
        redis_url = flask.current_app.config.get("REDIS_URL")
        r = Redis.from_url(redis_url)

        try:
            job = Job.fetch(job_id, connection=r)
        except NoSuchJobError:
            raise InvalidJobIdError("Job ID not found in the Redis Queue")

        return {"status": job.get_status().name}
