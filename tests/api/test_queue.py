import flask
import http
import sqlalchemy
import typing
import pytest
from unittest.mock import patch, MagicMock

from tests import DDSEndpoint, DEFAULT_HEADER, UserAuth, USER_CREDENTIALS
from dds_web.database import models
from dds_web import db
from dds_web.errors import InvalidJobIdError, DDSArgumentError
from dds_web.api.queue import JobInfo


def test_get_job_info_no_job_id(client):
    """Test getting job info without job_id"""
    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)
    response = client.get(tests.DDSEndpoint.QUEUE_JOB_INFO, headers=token)
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
    assert response.json["message"] == "No job_id provided"


@patch("dds_web.api.queue.Job.fetch")
def test_get_job_info_invalid_job_id(mock_fetch, client):
    """Test getting job info with invalid job_id"""

    from rq.exceptions import NoSuchJobError

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)

    with patch("dds_web.api.qeue.Job.fetch") as mock_fetch:
        mock_fetch.side_effect = NoSuchJobError()

        response = client.get(tests.DDSEndpoint.QUEUE_JOB_INFO, headers=token)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert response.json["message"] == "Job ID not found in the Redis Queue"


def test_get_job_info_success(client):
    """Test getting job info successfully"""

    token = tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client)

    with patch("dds_web.api.qeue.Job.fetch") as mock_fetch:

        mock_job = MagicMock()
        mock_job.get_status.return_value.name = "FINISHED"
        mock_fetch.return_value = mock_job

        response = client.get(
            tests.DDSEndpoint.QUEUE_JOB_INFO, headers=token, query_string={"job_id": "job_id"}
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json["status"] == "FINISHED"
