import http
import json
import uuid

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.padding import MGF1, OAEP
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
from cryptography.hazmat.primitives.hashes import SHA256

import dds_web
import tests
from dds_web.database import models
from dds_web.errors import (
    KeySetupError,
    KeyOperationError,
    KeyNotFoundError,
    SensitiveContentMissingError,
)
from dds_web.security.project_user_keys import (
    generate_invite_key_pair,
    generate_user_key_pair,
    share_project_private_key,
    verify_and_transfer_invite_to_user,
    update_user_keys_for_password_change,
)
from dds_web.security.tokens import encrypted_jwt_token
from dds_web.utils import timestamp
from tests.test_user_delete import user_from_email


def __padding():
    return OAEP(
        mgf=MGF1(algorithm=SHA256()),
        algorithm=SHA256(),
        label=None,
    )


def test_user_key_setup_error_with_salt(client):
    # user is created without a password, so salt will be missing
    user = models.User(username="testuser")
    with pytest.raises(KeySetupError) as error:
        generate_user_key_pair(user, "password")

    assert "User keys are not properly setup!" in str(error.value)


def test_user_key_setup_error_with_private_key(client):
    invite1 = models.Invite(email="new_unit_user@mailtrap.io", role="Unit Personnel")
    unituser = models.User.query.filter_by(username="unituser").first()
    unituser_token = encrypted_jwt_token(
        username=unituser.username,
        sensitive_content="password",
    )

    # Somehow private key has disappeared
    unituser.private_key = None

    with pytest.raises(KeySetupError) as error:
        share_project_private_key(
            from_user=unituser,
            to_another=invite1,
            from_user_token=unituser_token,
            project=unituser.unit.projects[0],
        )

    assert "User keys are not properly setup!" in str(error.value)


def test_user_key_setup_error_with_nonce(client):
    invite1 = models.Invite(email="new_unit_user@mailtrap.io", role="Unit Personnel")
    unituser = models.User.query.filter_by(username="unituser").first()
    unituser_token = encrypted_jwt_token(
        username=unituser.username,
        sensitive_content="password",
    )

    # Somehow nonce has disappeared
    unituser.nonce = None

    with pytest.raises(KeySetupError) as error:
        share_project_private_key(
            from_user=unituser,
            to_another=invite1,
            from_user_token=unituser_token,
            project=unituser.unit.projects[0],
        )

    assert "User keys are not properly setup!" in str(error.value)


def test_user_key_setup_error_with_public_key(client):
    invite1 = models.Invite(email="new_unit_user@mailtrap.io", role="Unit Personnel")

    # Somehow the key pair for the invite has not taken place or disappeared

    unituser = models.User.query.filter_by(username="unituser").first()
    unituser_token = encrypted_jwt_token(
        username=unituser.username,
        sensitive_content="password",
    )
    with pytest.raises(KeySetupError) as error:
        share_project_private_key(
            from_user=unituser,
            to_another=invite1,
            from_user_token=unituser_token,
            project=unituser.unit.projects[0],
        )

    assert "User keys are not properly setup!" in str(error.value)


def test_user_key_operation_error_with_load_user_public_key(client):
    invite1 = models.Invite(email="new_unit_user@mailtrap.io", role="Unit Personnel")
    generate_invite_key_pair(invite1)
    unituser = models.User.query.filter_by(username="unituser").first()
    unituser_token = encrypted_jwt_token(
        username=unituser.username,
        sensitive_content="password",
    )

    # Somehow the public key of the invite is not the expected public key
    invite1.public_key = b"useless_bytes"

    with pytest.raises(KeyOperationError) as error:
        share_project_private_key(
            from_user=unituser,
            to_another=invite1,
            from_user_token=unituser_token,
            project=unituser.unit.projects[0],
        )

    assert "User public key could not be loaded!" in str(error.value)


def test_user_key_operation_error_with_decrypt_user_private_key(client):
    invite1 = models.Invite(email="new_unit_user@mailtrap.io", role="Unit Personnel")
    unituser = models.User.query.filter_by(username="unituser").first()

    # Somehow a wrong password has ended up in the encrypted token
    unituser_token = encrypted_jwt_token(
        username=unituser.username,
        sensitive_content="passwor",
    )
    with pytest.raises(KeyOperationError) as error:
        share_project_private_key(
            from_user=unituser,
            to_another=invite1,
            from_user_token=unituser_token,
            project=unituser.unit.projects[0],
        )

    assert "User private key could not be decrypted!" in str(error.value)


def test_sensitive_content_missing_error(client):
    invite1 = models.Invite(email="new_unit_user@mailtrap.io", role="Unit Personnel")
    unituser = models.User.query.filter_by(username="unituser").first()

    # Somehow the password is missing in the encrypted token
    unituser_token = encrypted_jwt_token(
        username=unituser.username,
        sensitive_content=None,
    )
    with pytest.raises(SensitiveContentMissingError) as error:
        share_project_private_key(
            from_user=unituser,
            to_another=invite1,
            from_user_token=unituser_token,
            project=unituser.unit.projects[0],
        )

    assert "Sensitive content is missing in the encrypted token!" in str(error.value)


def test_user_key_not_found_error_for_project(client):
    project_without_keys = models.Project(
        public_id="random_project_id",
        title="random project_title",
        description="This is a random project. ",
        pi="PI",
        bucket=f"publicproj-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
    )

    # Somehow the key pair for the project is not created or persisted to the database

    invite1 = models.Invite(email="new_unit_user@mailtrap.io", role="Unit Personnel")
    unituser = models.User.query.filter_by(username="unituser").first()
    unituser.unit.projects.append(project_without_keys)
    dds_web.db.session.commit()
    unituser_token = encrypted_jwt_token(
        username=unituser.username,
        sensitive_content="password",
    )
    with pytest.raises(KeyNotFoundError) as error:
        share_project_private_key(
            from_user=unituser,
            to_another=invite1,
            from_user_token=unituser_token,
            project=project_without_keys,
        )

    assert "Unrecoverable key error. Aborting." in str(error.value)


def test_user_key_generation(client):
    user = models.User(username="testuser", password="password")
    assert user.public_key
    assert isinstance(serialization.load_der_public_key(user.public_key), RSAPublicKey)
    assert user.nonce
    assert user.private_key


def test_project_key_generation(client):
    # Setup is done in conftest.py
    project = models.Project.query.filter_by(public_id="public_project_id").first()
    assert project.public_key
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
    assert user.nonce
    assert user.private_key


def test_project_key_sharing(client):
    # Setup is done in conftest.py
    project = models.Project.query.filter_by(public_id="public_project_id").first()
    researchuser = models.User.query.filter_by(username="researchuser").first()
    project_researchuser_key = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id=researchuser.username
    ).first()
    assert project_researchuser_key
    assert researchuser.nonce
    assert researchuser.private_key

    unituser = models.User.query.filter_by(username="unituser").first()
    project_unituser_key = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id=unituser.username
    ).first()
    assert project_unituser_key
    assert unituser.nonce
    assert unituser.private_key


def test_delete_user_deletes_project_user_keys(client):
    """Unit Admin deletes unit user"""

    email_to_delete = "unituser2@mailtrap.io"

    project_unituser2_keys_before_delete = models.ProjectUserKeys.query.filter_by(
        user_id="unituser2"
    ).all()
    assert len(project_unituser2_keys_before_delete) == 5

    response = client.delete(
        tests.DDSEndpoint.USER_DELETE,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unitadmin"]).token(client),
        json={"email": email_to_delete},
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


def test_remove_user_from_project_deletes_project_user_keys(client):
    """Remove an associated user from a project"""

    username = "researchuser2"
    email = "researchuser2@mailtrap.io"
    public_id = "second_public_project_id"
    user_to_remove = {"email": email}
    project = models.Project.query.filter_by(public_id=public_id).first()
    assert project
    researchuser = models.User.query.filter_by(username=username).first()
    assert researchuser
    project_user_keys = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id=researchuser.username
    ).all()
    assert len(project_user_keys) == 1

    response = client.post(
        tests.DDSEndpoint.REMOVE_USER_FROM_PROJ,
        headers=tests.UserAuth(tests.USER_CREDENTIALS["unituser"]).token(client),
        query_string={"project": project.public_id},
        json=user_to_remove,
    )
    assert response.status_code == http.HTTPStatus.OK
    assert (
        f"User with email {email} no longer associated with {project.public_id}."
        in response.json["message"]
    )
    project_user_key = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id=researchuser.username
    ).first()
    assert not project_user_key


def test_share_project_keys_via_two_invites(client):
    # this test focuses only on the secure parts related to the following scenario

    # unituser invites a new Unit Personnel
    invite1 = models.Invite(email="new_unit_user@mailtrap.io", role="Unit Personnel")
    temporary_key = generate_invite_key_pair(invite1)
    invite_token1 = encrypted_jwt_token(
        username="",
        sensitive_content=temporary_key.hex(),
        additional_claims={"inv": invite1.email},
    )
    unituser = models.User.query.filter_by(username="unituser").first()
    unituser.unit.invites.append(invite1)
    unituser_token = encrypted_jwt_token(
        username=unituser.username,
        sensitive_content="password",
    )
    for project in unituser.unit.projects:
        share_project_private_key(
            from_user=unituser,
            to_another=invite1,
            from_user_token=unituser_token,
            project=project,
        )
    dds_web.db.session.commit()

    # ************************************

    # invited Unit Personnel follows the link and registers itself
    common_user_fields = {
        "username": "user_not_existing",
        "password": "Password123",
        "name": "Test User",
    }
    new_user = models.UnitUser(**common_user_fields)
    invite1.unit.users.append(new_user)
    new_email = models.Email(email=invite1.email, primary=True)
    new_user.emails.append(new_email)
    new_user.active = True
    dds_web.db.session.add(new_user)
    verify_and_transfer_invite_to_user(invite_token1, new_user, common_user_fields["password"])
    for project_invite_key in invite1.project_invite_keys:
        project_user_key = models.ProjectUserKeys(
            project_id=project_invite_key.project_id,
            user_id=new_user.username,
            key=project_invite_key.key,
        )
        dds_web.db.session.add(project_user_key)
        dds_web.db.session.delete(project_invite_key)

    assert invite1.nonce != new_user.nonce
    assert invite1.public_key == new_user.public_key
    assert invite1.private_key != new_user.private_key

    dds_web.db.session.delete(invite1)
    dds_web.db.session.commit()

    # ************************************

    # new Unit Personnel invites another new Unit Personnel
    invite2 = models.Invite(email="another_unit_user@mailtrap.io", role="Unit Personnel")
    invite_token2 = encrypted_jwt_token(
        username="",
        sensitive_content=generate_invite_key_pair(invite2).hex(),
        additional_claims={"inv": invite2.email},
    )
    unituser = models.User.query.filter_by(username="user_not_existing").first()
    unituser.unit.invites.append(invite2)
    unituser_token = encrypted_jwt_token(
        username=unituser.username,
        sensitive_content=common_user_fields["password"],
    )
    for project in unituser.unit.projects:
        share_project_private_key(
            from_user=unituser,
            to_another=invite2,
            from_user_token=unituser_token,
            project=project,
        )
    dds_web.db.session.commit()

    project_invite_keys = invite2.project_invite_keys
    number_of_asserted_projects = 0
    for project_invite_key in project_invite_keys:
        if (
            project_invite_key.project.public_id == "public_project_id"
            or project_invite_key.project.public_id == "unused_project_id"
            or project_invite_key.project.public_id == "restricted_project_id"
            or project_invite_key.project.public_id == "second_public_project_id"
            or project_invite_key.project.public_id == "file_testing_project"
        ):
            number_of_asserted_projects += 1
    assert len(project_invite_keys) == number_of_asserted_projects
    assert len(project_invite_keys) == 5


def test_update_user_keys_for_password_change(client):
    user = models.User(username="randomtestuser", password="password")

    public_key_initial = user.public_key
    nonce_initial = user.nonce
    private_key_initial = user.private_key
    kd_salt_initial = user.kd_salt

    assert public_key_initial
    assert nonce_initial
    assert private_key_initial
    assert kd_salt_initial

    update_user_keys_for_password_change(user, "password", "bogus")
    user.password = "bogus"

    public_key_after_password_change = user.public_key
    nonce_after_password_change = user.nonce
    private_key_after_password_change = user.private_key
    kd_salt_after_password_change = user.kd_salt

    assert public_key_after_password_change
    assert nonce_after_password_change
    assert private_key_after_password_change
    assert kd_salt_after_password_change

    assert public_key_after_password_change == public_key_initial
    assert nonce_after_password_change != nonce_initial
    assert private_key_after_password_change != private_key_initial
    assert kd_salt_after_password_change != kd_salt_initial

    # It shouldn't matter whichever comes first between set password
    # and update user keys as the password is not stored in database

    user.password = "password"
    update_user_keys_for_password_change(user, "bogus", "password")

    public_key_final = user.public_key
    nonce_final = user.nonce
    private_key_final = user.private_key
    kd_salt_final = user.kd_salt

    assert public_key_final
    assert nonce_final
    assert private_key_final
    assert kd_salt_final

    assert public_key_final == public_key_initial
    assert nonce_final != nonce_initial
    assert private_key_final != private_key_initial
    assert kd_salt_final != kd_salt_initial

    assert public_key_after_password_change == public_key_final
    assert nonce_after_password_change != nonce_final
    assert private_key_after_password_change != private_key_final
    assert kd_salt_after_password_change != kd_salt_final
