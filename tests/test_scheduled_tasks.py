import flask

import pytest

from dds_web import db
from dds_web.database import models

from dds_web.scheduled_tasks import delete_invite


def test_delete_invite(client: flask.testing.FlaskClient) -> None:
    assert len(db.session.query(models.Invite).all()) == 2
    delete_invite()
    assert len(db.session.query(models.Invite).all()) == 1
