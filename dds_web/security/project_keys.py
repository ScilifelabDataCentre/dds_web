""" Code for generating project related keys """
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
    derived_key = argon2.low_level.hash_secret_raw(secret=password.encode(),
                                                   salt=user.kd_salt,
                                                   time_cost=2,
                                                   memory_cost=1048576,  # 4194304,
                                                   parallelism=8,
                                                   hash_len=32,
                                                   type=argon2.Type.ID)
    if len(derived_key) != 32:
        exception = Exception("Derived key is not 256 bits long!")
        flask.current_app.logger.exception(exception)
        raise exception
    return derived_key


def obtain_project_private_key(user, project_key):
    password = dds_web.cache.get(user.username)
    if password is None:
        raise Exception("Sensitive content is missing in token!")
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


class ProjectKeys:
    """Class with methods to generate keys"""

    def __init__(self, project_id):
        """Needs a project id"""
        self.project_id = project_id
        self._generate_keypair()

    def key_dict(self):
        return dict(
            public_key=self._public_key_bytes.hex().upper(),
        )

    def _generate_keypair(self):
        """Generates salted, encrypted private and public key"""
        project_key_gen = cryptography.hazmat.primitives.asymmetric.x25519.X25519PrivateKey.generate()
        # generate private key bytes
        private_key_bytes = project_key_gen.private_bytes(
            encoding=cryptography.hazmat.primitives.serialization.Encoding.Raw,
            format=cryptography.hazmat.primitives.serialization.PrivateFormat.Raw,
            encryption_algorithm=cryptography.hazmat.primitives.serialization.NoEncryption(),
        )

        # Generate public key bytes
        self._public_key_bytes = project_key_gen.public_key().public_bytes(
            encoding=cryptography.hazmat.primitives.serialization.Encoding.Raw,
            format=cryptography.hazmat.primitives.serialization.PublicFormat.Raw
        )

        # encrypt private_key_bytes

        # persist encrypted private_key_bytes

        # destroy private_key_bytes

        # destroy project_key_gen
