""" Code for generating project related keys """

from os import urandom

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf import scrypt
from nacl import bindings
from flask import current_app


class ProjectKeys:
    """Class with methods to generate keys"""

    def __init__(self, project_id):
        """Needs a project id"""
        self.project_id = project_id
        self._projectid_to_bytes()
        self._gen_salt_and_nonce()
        self._set_passphrase()
        self._generate_keypair()

    def key_dict(self):
        return dict(
            privkey_salt=self._salt.hex().upper(),
            privkey_nonce=self._nonce.hex().upper(),
            private_key=self._encrypted_private_key.hex().upper(),
            public_key=self._public_key_bytes.hex().upper(),
        )

    def _projectid_to_bytes(self):
        """Converts and set the project id in bytes"""
        self._project_id_bytes = bytes(self.project_id, "utf-8")

    def _gen_salt_and_nonce(self):
        """Set salt and nonce i.e. random generated bit for encryption"""
        self._salt = urandom(16)
        self._nonce = urandom(12)

    def _set_passphrase(self):
        """Sets the private encryption passphrase using app secret key"""
        self._passphrase = (current_app.config.get("SECRET_KEY")).encode("utf-8")

    def _generate_keypair(self):
        """Generates salted, encrypted private and public key"""
        project_key_gen = x25519.X25519PrivateKey.generate()
        # generate private key bytes
        private_key_bytes = project_key_gen.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        # Massage the passphrase to be used for encryption using scrypt
        scrpyt_salt = scrypt.Scrypt(
            salt=self._salt,
            length=32,
            n=2 ** 14,
            r=8,
            p=1,
            backend=backends.default_backend(),
        )
        derived_passphrase_key = scrpyt_salt.derive(self._passphrase)
        # Encrypt the formatted private key with salted passphrase and nonce
        self._encrypted_private_key = bindings.crypto_aead_chacha20poly1305_ietf_encrypt(
            message=private_key_bytes,
            aad=None,
            nonce=self._nonce,
            key=derived_passphrase_key,
        )
        # Generate public key bytes
        self._public_key_bytes = project_key_gen.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
