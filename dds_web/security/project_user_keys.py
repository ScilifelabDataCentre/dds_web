""" Code for generating and maintaining project and user related keys """
import os

import argon2
import cryptography.exceptions
from cryptography.hazmat.primitives import asymmetric, ciphers, hashes, serialization
import flask
import gc

from dds_web.database import models
from dds_web.errors import (
    KeyNotFoundError,
    KeyOperationError,
    KeySetupError,
    SensitiveContentMissingError,
)
from dds_web.security.auth import (
    extract_encrypted_token_sensitive_content,
    extract_token_invite_key,
)


def __derive_key(user, password):
    if not user.kd_salt:
        raise KeySetupError(message="User keys are not properly setup!")

    derived_key = argon2.low_level.hash_secret_raw(
        secret=password.encode(),
        salt=user.kd_salt,
        time_cost=2,
        memory_cost=flask.current_app.config["ARGON_KD_MEMORY_COST"],
        parallelism=8,
        hash_len=32,
        type=argon2.Type.ID,
    )

    if len(derived_key) != 32:
        raise KeySetupError(message="Derived key is not 256 bits long!")

    return derived_key


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


def __encrypt_project_private_key(owner, project_private_key):
    if not owner.public_key:
        raise KeySetupError(message="User keys are not properly setup!")

    try:
        owner_public_key = serialization.load_der_public_key(owner.public_key)
        if isinstance(owner_public_key, asymmetric.rsa.RSAPublicKey):
            return __encrypt_with_rsa(project_private_key, owner_public_key)
    except ValueError as exc:
        raise KeyOperationError(message="User public key could not be loaded!") from exc


def __decrypt_project_private_key(user, token, encrypted_project_private_key):
    private_key_bytes = __decrypt_user_private_key_via_token(user, token)
    if not private_key_bytes:
        raise KeyOperationError(message="User private key could not be decrypted!")

    try:
        user_private_key = serialization.load_der_private_key(private_key_bytes, password=None)
        if isinstance(user_private_key, asymmetric.rsa.RSAPrivateKey):
            return __decrypt_with_rsa(encrypted_project_private_key, user_private_key)
    except ValueError as exc:
        raise KeyOperationError(message="User private key could not be loaded!") from exc


def obtain_project_private_key(user, project, token):
    project_key = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id=user.username
    ).first()
    if project_key:
        return __decrypt_project_private_key(user, token, project_key.key)
    raise KeyNotFoundError(project=project.public_id)


def share_project_private_key(
    from_user, to_another, from_user_token, project, is_project_owner=False
):
    if isinstance(to_another, models.Invite):
        __init_and_append_project_invite_key(
            invite=to_another,
            project=project,
            project_private_key=obtain_project_private_key(
                user=from_user, project=project, token=from_user_token
            ),
            is_project_owner=is_project_owner,
        )
    else:
        __init_and_append_project_user_key(
            user=to_another,
            project=project,
            project_private_key=obtain_project_private_key(
                user=from_user, project=project, token=from_user_token
            ),
        )


def __init_and_append_project_user_key(user, project, project_private_key):
    project_user_key = models.ProjectUserKeys(
        project_id=project.id,
        user_id=user.username,
        key=__encrypt_project_private_key(user, project_private_key),
    )
    user.project_user_keys.append(project_user_key)
    project.project_user_keys.append(project_user_key)


def __init_and_append_project_invite_key(
    invite, project, project_private_key, is_project_owner=False
):
    """Save encrypted project private key to ProjectInviteKeys."""
    project_invite_key = models.ProjectInviteKeys(
        project_id=project.id,
        invite_id=invite.id,
        key=__encrypt_project_private_key(owner=invite, project_private_key=project_private_key),
        owner=is_project_owner,
    )
    invite.project_invite_keys.append(project_invite_key)
    project.project_invite_keys.append(project_invite_key)


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
    try:
        aesgcm = ciphers.aead.AESGCM(key=key)
        return aesgcm.decrypt(nonce=nonce, data=ciphertext, associated_data=aad)
    except (cryptography.exceptions.InvalidTag, ValueError):
        return None


def __owner_identifier(owner):
    return owner.email if isinstance(owner, models.Invite) else owner.username


def __encrypt_owner_private_key(owner, private_key, owner_key=None):
    """Encrypt owners private key."""
    # Generate key or use current key if exists
    key = owner_key or ciphers.aead.AESGCM.generate_key(bit_length=256)

    # Encrypt private key
    nonce, encrypted_key = __encrypt_with_aes(
        key=key,
        plaintext=private_key,
        aad=b"private key for " + __owner_identifier(owner=owner).encode(),
    )

    # Save nonce and private key to database
    owner.nonce = nonce
    owner.private_key = encrypted_key

    return key


def __decrypt_user_private_key(user, user_key):
    if user.private_key and user.nonce:
        return __decrypt_with_aes(
            user_key,
            user.private_key,
            user.nonce,
            aad=b"private key for " + user.username.encode(),
        )
    raise KeySetupError(message="User keys are not properly setup!")


def __decrypt_user_private_key_via_token(user, token):
    password = extract_encrypted_token_sensitive_content(token, user.username)
    if not password:
        raise SensitiveContentMissingError
    user_key = __derive_key(user, password)

    return __decrypt_user_private_key(user, user_key)


def __decrypt_invite_private_key(invite, temporary_key):
    """Decrypt invite private key."""
    if temporary_key and invite.private_key and invite.nonce:
        return __decrypt_with_aes(
            key=temporary_key,
            ciphertext=invite.private_key,
            nonce=invite.nonce,
            aad=b"private key for " + invite.email.encode(),
        )


def update_user_keys_for_password_change(user, current_password, new_password):
    """
    Updates the user key (key encryption key) and the encrypted user private key

    :param user: a user object from the models, its password is about to change
    :param current_password: the password that is being replaced. It is expected to be validated via its web form.
    :param new_password: the password that is replacing the previous one. It is expected to be validated via its web form.
    """
    old_user_key = __derive_key(user, current_password)
    private_key_bytes = __decrypt_user_private_key(user, old_user_key)
    if not private_key_bytes:
        raise KeyOperationError(message="User private key could not be decrypted!")

    user.kd_salt = os.urandom(32)
    new_user_key = __derive_key(user, new_password)
    __encrypt_owner_private_key(user, private_key_bytes, new_user_key)

    del new_user_key
    del old_user_key
    del private_key_bytes
    gc.collect()


def verify_and_transfer_invite_to_user(token, user, password):
    invite, temporary_key = extract_token_invite_key(token)
    private_key_bytes = __verify_invite_temporary_key(invite, temporary_key)
    if private_key_bytes:
        __transfer_invite_private_key_to_user(invite, private_key_bytes, user, password)
        del private_key_bytes
        gc.collect()
        return True
    return False


def __transfer_invite_private_key_to_user(invite, private_key_bytes, user, password):
    user_key = __derive_key(user, password)
    __encrypt_owner_private_key(user, private_key_bytes, user_key)
    user.public_key = invite.public_key
    del user_key
    gc.collect()


def __verify_invite_temporary_key(invite, temporary_key):
    """Verify the temporary key generated for the specific user invite."""
    private_key_bytes = __decrypt_invite_private_key(invite=invite, temporary_key=temporary_key)
    if private_key_bytes and isinstance(
        serialization.load_der_private_key(data=private_key_bytes, password=None),
        asymmetric.rsa.RSAPrivateKey,
    ):
        return private_key_bytes
    return None


def __generate_rsa_key_pair(owner):
    """Generate RSA key pair."""
    # Generate keys and get them in bytes
    private_key = asymmetric.rsa.generate_private_key(public_exponent=65537, key_size=4096)
    private_key_bytes = private_key.private_bytes(
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    public_key_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Set row public key
    owner.public_key = public_key_bytes

    # Clean up sensitive information
    del private_key
    gc.collect()

    return private_key_bytes


def generate_user_key_pair(user, password):
    private_key_bytes = __generate_rsa_key_pair(user)
    user_key = __derive_key(user, password)
    __encrypt_owner_private_key(user, private_key_bytes, user_key)
    del user_key
    del private_key_bytes
    gc.collect()


def generate_invite_key_pair(invite):
    """Generate new Key Pair for invited user."""
    # Generate keys
    private_key_bytes = __generate_rsa_key_pair(owner=invite)

    # Generate temporary key and encrypt private key
    temporary_key = __encrypt_owner_private_key(owner=invite, private_key=private_key_bytes)

    # Clean up sensitive information
    del private_key_bytes
    gc.collect()

    return temporary_key
