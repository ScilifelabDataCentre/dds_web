""" Code for generating and maintaining project and user related keys """
import os

from cryptography.hazmat.primitives import asymmetric, ciphers, hashes, serialization
import flask
import gc

from dds_web.database import models
from dds_web.errors import KeyNotFoundError


def __get_padding_for_rsa():
    """
    This is the recommended padding algorithm for RSA encryption at the time of implementation.
    [https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/#cryptography.hazmat.primitives.asymmetric.padding.OAEP]
    """
    return asymmetric.padding.OAEP(
        mgf=asymmetric.padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    )


def __encrypt_with_rsa(plaintext, public_key):
    """
    Encrypts the plaintext with the RSA algorithm using the public key
    :param plaintext: a byte string
    :param public_key: public key of the user
    """
    return public_key.encrypt(plaintext, __get_padding_for_rsa())


def __decrypt_with_rsa(ciphertext, private_key):
    """
    Decrypts the ciphertext with the RSA algorithm using the private key
    :param ciphertext: encrypted content
    :param private_key: private key of the user
    """
    return private_key.decrypt(ciphertext, __get_padding_for_rsa())


def __encrypt_project_private_key_for_user(user, project_private_key):
    user_public_key = serialization.load_der_public_key(user.public_key)
    if isinstance(user_public_key, asymmetric.rsa.RSAPublicKey):
        return __encrypt_with_rsa(project_private_key, user_public_key)
    exception = Exception("User public key cannot be loaded!")
    flask.current_app.logger.exception(exception)
    raise exception


def __decrypt_project_private_key_for_user(user, encrypted_project_private_key):
    user_private_key = serialization.load_der_private_key(
        __decrypt_user_private_key(user), password=None
    )
    if isinstance(user_private_key, asymmetric.rsa.RSAPrivateKey):
        return __decrypt_with_rsa(encrypted_project_private_key, user_private_key)
    exception = Exception("User private key cannot be loaded!")
    flask.current_app.logger.exception(exception)
    raise exception


def obtain_project_private_key(user, project):
    project_key = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id=user.username
    ).first()
    if project_key:
        return __decrypt_project_private_key_for_user(user, project_key.key)
    raise KeyNotFoundError(project=project.public_id)


def share_project_private_key_with_user(current_user, existing_user, project):
    __init_and_append_project_user_key(
        existing_user, project, obtain_project_private_key(current_user, project)
    )


def __init_and_append_project_user_key(user, project, project_private_key):
    project_user_key = models.ProjectUserKeys(
        project_id=project.id,
        user_id=user.username,
        key=__encrypt_project_private_key_for_user(user, project_private_key),
    )
    user.project_user_keys.append(project_user_key)
    project.project_user_keys.append(project_user_key)


def generate_project_key_pair(user, project):
    private_key = asymmetric.x25519.X25519PrivateKey.generate()
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    project.public_key = public_key_bytes
    for unit_user in user.unit.users:
        __init_and_append_project_user_key(unit_user, project, private_key_bytes)
    del private_key_bytes
    del private_key
    gc.collect()


def __encrypt_with_aes(key, plaintext, aad=None):
    """
    Encrypts the plaintext with the AES algorithm using the key
    :param key: symmetric key of the user
    :param plaintext: a byte string
    :param aad: Additional data that should be authenticated with the key, but is not encrypted. Can be None.
    """
    aesgcm = ciphers.aead.AESGCM(key)
    nonce = os.urandom(12)
    return nonce, aesgcm.encrypt(nonce, plaintext, aad)


def __decrypt_with_aes(key, ciphertext, nonce, aad=None):
    """
    Decrypts the ciphertext with the AES algorithm using the key
    :param key: symmetric key of the user
    :param ciphertext: encrypted content
    :param nonce: a unique value that has to be used only once to encrypt a given data with the given key
    :param aad: Additional data that should be authenticated with the key, but is not encrypted. Can be None.
    """
    aesgcm = ciphers.aead.AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, aad)


def __owner_identifier(owner):
    return owner.email if isinstance(owner, models.Invite) else owner.username


def __encrypt_owner_private_key(owner, private_key):
    temporary_key = ciphers.aead.AESGCM.generate_key(bit_length=256)
    nonce, encrypted_key = __encrypt_with_aes(
        temporary_key, private_key, aad=b"private key for " + __owner_identifier(owner).encode()
    )
    owner.nonce = nonce
    owner.private_key = encrypted_key
    return temporary_key


def __encrypt_user_private_key(user, private_key):
    user.temporary_key = __encrypt_owner_private_key(user, private_key)


def __decrypt_user_private_key(user):
    if user.temporary_key and user.private_key and user.nonce:
        return __decrypt_with_aes(
            user.temporary_key,
            user.private_key,
            user.nonce,
            aad=b"private key for " + user.username.encode(),
        )
    exception = Exception("User account is not properly setup!")
    flask.current_app.logger.exception(exception)
    raise exception


def __encrypt_invite_private_key(invite, private_key):
    return __encrypt_owner_private_key(invite, private_key)


def __generate_rsa_key_pair(owner):
    private_key = asymmetric.rsa.generate_private_key(public_exponent=65537, key_size=4096)
    private_key_bytes = private_key.private_bytes(
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    public_key_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    owner.public_key = public_key_bytes
    del private_key
    gc.collect()
    return private_key_bytes


def generate_user_key_pair(user):
    private_key_bytes = __generate_rsa_key_pair(user)
    __encrypt_user_private_key(user, private_key_bytes)
    del private_key_bytes
    gc.collect()


def generate_invite_key_pair(invite):
    private_key_bytes = __generate_rsa_key_pair(invite)
    temporary_key = __encrypt_invite_private_key(invite, private_key_bytes)
    del private_key_bytes
    gc.collect()
    return temporary_key
