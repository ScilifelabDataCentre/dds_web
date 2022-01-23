""" Code for generating project related keys """
import os

import argon2
import cryptography
import flask
import gc

import dds_web
from dds_web.api.errors import KeyNotFoundError


def derive_key(user, password):
    if user.kd_salt is None:
        exception = Exception("Access to project data is not properly setup for the user!")
        flask.current_app.logger.exception(exception)
        raise exception
    derived_key = argon2.low_level.hash_secret_raw(
        secret=password.encode(),
        salt=user.kd_salt,
        time_cost=2,
        memory_cost=1048576,  # 4194304,
        parallelism=8,
        hash_len=32,
        type=argon2.Type.ID,
    )
    if len(derived_key) != 32:
        exception = Exception("Derived key is not 256 bits long!")
        flask.current_app.logger.exception(exception)
        raise exception
    return derived_key


def manage_project_key_among_users(existing_user, current_user, project_key):
    return encrypt_project_key(existing_user, obtain_project_private_key(current_user, project_key))


def obtain_project_private_key(user, project_key):
    password = dds_web.cache.get(user.username)
    key_encryption_key = derive_key(user, password)
    try:
        aesgcm = cryptography.hazmat.primitives.ciphers.aead.AESGCM(key_encryption_key)
        aad = b"project key for user " + user.username.encode()
        dds_web.cache.delete(user.username)
        del password
        del key_encryption_key
        gc.collect()
        return aesgcm.decrypt(project_key.nonce, project_key.key, aad)
    except Exception as err:
        flask.current_app.logger.exception(err)
        raise KeyNotFoundError


def encrypt_project_key(user, user_key, project_private_key):
    aad = b"project key for user " + user.username.encode()
    aesgcm = cryptography.hazmat.primitives.ciphers.aead.AESGCM(user_key)
    nonce = os.urandom(12)
    return {"nonce": nonce, "encrypted_key": aesgcm.encrypt(nonce, project_private_key, aad)}


def encrypt_project_key_with_temp_key(user, project_private_key):
    if user.temporary_key is None:
        user.temporary_key = cryptography.hazmat.primitives.ciphers.aead.AESGCM.generate_key(
            bit_length=256
        )
    return encrypt_project_key(user, user.temporary_key, project_private_key)


def encrypt_project_key_with_password(user, project_private_key):
    password = dds_web.cache.get(user.username)
    user_key = derive_key(user, password)
    dds_web.cache.delete(user.username)
    encrypted_project_key = encrypt_project_key(user, user_key, project_private_key)
    del password
    del user_key
    gc.collect()
    return encrypted_project_key


def generate_project_key_pair(user):
    private_key = cryptography.hazmat.primitives.asymmetric.x25519.X25519PrivateKey.generate()

    private_key_bytes = private_key.private_bytes(
        encoding=cryptography.hazmat.primitives.serialization.Encoding.Raw,
        format=cryptography.hazmat.primitives.serialization.PrivateFormat.Raw,
        encryption_algorithm=cryptography.hazmat.primitives.serialization.NoEncryption(),
    )

    public_key_bytes = private_key.public_key().public_bytes(
        encoding=cryptography.hazmat.primitives.serialization.Encoding.Raw,
        format=cryptography.hazmat.primitives.serialization.PublicFormat.Raw,
    )

    encrypted_private_key = encrypt_project_key_with_password(user, private_key_bytes)

    del private_key_bytes
    del private_key
    gc.collect()

    return {"public_key": public_key_bytes, "encrypted_private_key": encrypted_private_key}
