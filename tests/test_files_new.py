import json
from dds_web import db
import dds_web.utils
from dds_web.database import models
import tests

first_new_file = {
    "name": "filename1",
    "name_in_bucket": "filebucketname1",
    "subpath": "subpath",
    "size": 1000,
    "size_processed": 500,
    "compressed": True,
    "public_key": "publickey",
    "salt": "salt",
    "checksum": "checksum",
}


def test_new_file(client):
    """Add file to database."""

    project_1 = (
        db.session.query(models.Project).filter_by(public_id="file_testing_project").one_or_none()
    )
    assert project_1

    response = client.post(
        tests.DDSEndpoint.FILE_NEW,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).post_headers(),
        query_string={"project": "file_testing_project"},
        data=json.dumps(first_new_file),
        content_type="application/json",
    )
    assert response.status == "200 OK"

    assert (
        db.session.query(models.File)
        .filter_by(
            name=first_new_file["name"],
            name_in_bucket=first_new_file["name_in_bucket"],
            subpath=first_new_file["subpath"],
            size_original=first_new_file["size"],
            size_stored=first_new_file["size_processed"],
            compressed=first_new_file["compressed"],
            public_key=first_new_file["public_key"],
            salt=first_new_file["salt"],
            checksum=first_new_file["checksum"],
            project_id=project_1.id,
        )
        .one_or_none()
    )
