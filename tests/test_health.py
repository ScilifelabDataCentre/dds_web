import http

import tests


def test_status(client):
    """
    Confirm that the status endpoint is working.
    """
    response = client.get(tests.DDSEndpoint.STATUS)
    assert response.status_code == http.HTTPStatus.OK
    assert response.json["status"] == "ready"
