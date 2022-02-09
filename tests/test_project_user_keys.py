import http
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.padding import MGF1, OAEP
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey, X25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256

import dds_web
import tests
from dds_web.database import models
from tests.test_user_delete import user_from_email


def __aes_decrypt(user):
    aesgcm = AESGCM(user.temporary_key)
    return aesgcm.decrypt(
        user.nonce, user.private_key, b"private key for user " + user.username.encode()
    )


def __padding():
    return OAEP(
        mgf=MGF1(algorithm=SHA256()),
        algorithm=SHA256(),
        label=None,
    )


def test_user_key_generation(client):
    user = models.User(username="testuser")
    assert user.public_key is not None
    assert isinstance(serialization.load_der_public_key(user.public_key), RSAPublicKey)
    assert user.temporary_key is not None
    assert user.nonce is not None
    assert user.private_key is not None
    private_key_bytes = __aes_decrypt(user)
    assert isinstance(
        serialization.load_der_private_key(private_key_bytes, password=None), RSAPrivateKey
    )


def test_project_key_generation(client):
    # Setup is done in conftest.py
    project = models.Project.query.filter_by(public_id="public_project_id").first()
    assert project.public_key is not None
    assert isinstance(X25519PublicKey.from_public_bytes(project.public_key), X25519PublicKey)
    number_of_unitusers_with_project_key = 0
    project_user_keys = project.project_user_keys
    for project_user_key in project_user_keys:
        if (
            project_user_key.user_id == "unituser"
            or project_user_key.user_id == "unituser2"
            or project_user_key.user_id == "unitadmin"
        ):
            number_of_unitusers_with_project_key += 1
    assert number_of_unitusers_with_project_key == 3
    user = project_user_keys[0].user
    assert user.temporary_key is not None
    assert user.nonce is not None
    assert user.private_key is not None
    user_private_key_bytes = __aes_decrypt(user)
    user_private_key = serialization.load_der_private_key(user_private_key_bytes, password=None)
    project_private_key_bytes = user_private_key.decrypt(project_user_keys[0].key, __padding())
    assert isinstance(
        X25519PrivateKey.from_private_bytes(project_private_key_bytes), X25519PrivateKey
    )


def test_project_key_sharing(client):
    # Setup is done in conftest.py
    project = models.Project.query.filter_by(public_id="public_project_id").first()
    researchuser = models.User.query.filter_by(username="researchuser").first()
    project_researchuser_key = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id=researchuser.username
    ).first()
    assert project_researchuser_key is not None
    assert researchuser.temporary_key is not None
    assert researchuser.nonce is not None
    assert researchuser.private_key is not None
    researchuser_private_key_bytes = __aes_decrypt(researchuser)
    researchuser_private_key = serialization.load_der_private_key(
        researchuser_private_key_bytes, password=None
    )
    project_private_key_bytes = researchuser_private_key.decrypt(
        project_researchuser_key.key, __padding()
    )

    unituser = models.User.query.filter_by(username="unituser").first()
    project_unituser_key = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id=unituser.username
    ).first()
    assert project_unituser_key is not None
    assert unituser.temporary_key is not None
    assert unituser.nonce is not None
    assert unituser.private_key is not None
    unituser_private_key_bytes = __aes_decrypt(unituser)
    unituser_private_key = serialization.load_der_private_key(
        unituser_private_key_bytes, password=None
    )
    assert (
        unituser_private_key.decrypt(project_unituser_key.key, __padding())
        == project_private_key_bytes
    )


def test_delete_user_deletes_project_user_keys(client):
    """Unit admin deletes unit user"""

    email_to_delete = "unituser2@mailtrap.io"

    project_unituser2_keys_before_delete = models.ProjectUserKeys.query.filter_by(
        user_id="unituser2"
    ).all()
    assert len(project_unituser2_keys_before_delete) == 5

    response = client.delete(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        data=json.dumps({"email": email_to_delete}),
        content_type="application/json",
    )
    assert response.status_code == http.HTTPStatus.OK

    # Make sure that user was deleted
    exists = user_from_email(email_to_delete)
    assert exists is None
    assert dds_web.utils.email_in_db(email_to_delete) is False

    project_unituser2_keys_after_delete = models.ProjectUserKeys.query.filter_by(
        user_id="unituser2"
    ).all()
    assert len(project_unituser2_keys_after_delete) == 0
