""" Code for generating and maintaining project and user related keys """
import os

import cryptography.exceptions
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
    return public_key.encrypt(plaintext=plaintext, padding=__get_padding_for_rsa())


def __decrypt_with_rsa(ciphertext, private_key):
    """
    Decrypts the ciphertext with the RSA algorithm using the private key
    :param ciphertext: encrypted content
    :param private_key: private key of the user
    """
    return private_key.decrypt(ciphertext=ciphertext, padding=__get_padding_for_rsa())


def __encrypt_project_private_key(owner, project_private_key):
    """Encrypt Project Private key."""
    # Load key and verify correct format
    public_key = serialization.load_der_public_key(data=owner.public_key)
    if isinstance(public_key, asymmetric.rsa.RSAPublicKey):
        return __encrypt_with_rsa(plaintext=project_private_key, public_key=public_key)
    # TODO: Change exception type
    exception = Exception("Public key cannot be loaded for encrypting the project private key!")
    flask.current_app.logger.exception(exception)
    raise exception


def __decrypt_project_private_key(user, encrypted_project_private_key):
    """Decrypt Project Private Key."""
    # Load key and verify correct format
    user_private_key = serialization.load_der_private_key(
        data=__decrypt_user_private_key(user=user), password=None
    )
    if isinstance(user_private_key, asymmetric.rsa.RSAPrivateKey):
        return __decrypt_with_rsa(
            ciphertext=encrypted_project_private_key, private_key=user_private_key
        )
    exception = Exception("User private key cannot be loaded!")
    flask.current_app.logger.exception(exception)
    raise exception


def obtain_project_private_key(user, project):
    """Get Project Private key from database."""
    project_key = models.ProjectUserKeys.query.filter_by(
        project_id=project.id, user_id=user.username
    ).first()
    # Verify that project key row exists - user has access
    if project_key:
        return __decrypt_project_private_key(
            user=user, encrypted_project_private_key=project_key.key
        )
    raise KeyNotFoundError(project=project.public_id)


def share_project_private_key(from_user, to_another, project):
    """Share project private key and there for access to project data."""
    if isinstance(to_another, models.Invite):
        __init_and_append_project_invite_key(
            invite=to_another,
            project=project,
            project_private_key=obtain_project_private_key(user=from_user, project=project),
        )
    else:
        __init_and_append_project_user_key(
            user=to_another,
            project=project,
            project_private_key=obtain_project_private_key(user=from_user, project=project),
        )


def __init_and_append_project_user_key(user, project, project_private_key):
    """Set new project user key row - give user access to project data."""
    project_user_key = models.ProjectUserKeys(
        project_id=project.id,
        user_id=user.username,
        key=__encrypt_project_private_key(owner=user, project_private_key=project_private_key),
    )
    user.project_user_keys.append(project_user_key)
    project.project_user_keys.append(project_user_key)


def __init_and_append_project_invite_key(invite, project, project_private_key):
    """Set new project invite key - invite user to project."""
    project_invite_key = models.ProjectInviteKeys(
        project_id=project.id,
        invite_id=invite.id,
        key=__encrypt_project_private_key(owner=invite, project_private_key=project_private_key),
    )
    invite.project_invite_keys.append(project_invite_key)
    project.project_invite_keys.append(project_invite_key)


def generate_project_key_pair(user, project):
    """Generate new Project Key Pair."""
    # Generate key pair and get keys as bytes
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
    # Set project public key
    project.public_key = public_key_bytes

    # Give all unit users access to the project -- new own copy of project private, encrypted
    for unit_user in user.unit.users:
        __init_and_append_project_user_key(
            user=unit_user, project=project, project_private_key=private_key_bytes
        )

    # Clean up sensitive information
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
    aesgcm = ciphers.aead.AESGCM(key=key)
    nonce = os.urandom(12)
    return nonce, aesgcm.encrypt(nonce=nonce, data=plaintext, associated_data=aad)


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
    """Return email if invite or username if user."""
    return owner.email if isinstance(owner, models.Invite) else owner.username


def __encrypt_owner_private_key(owner, private_key, temporary_key=None):
    """Encrypt Private Key of owner - either user or invitee."""
    if temporary_key is None:
        temporary_key = ciphers.aead.AESGCM.generate_key(bit_length=256)
    nonce, encrypted_key = __encrypt_with_aes(
        key=temporary_key,
        plaintext=private_key,
        aad=b"private key for " + __owner_identifier(owner=owner).encode(),
    )

    # Set nonce and encrypted private key in database
    owner.nonce = nonce
    owner.private_key = encrypted_key

    return temporary_key


def __encrypt_user_private_key(user, private_key):
    """Encrypt User Private Key."""
    # Set user temporary key
    user.temporary_key = __encrypt_owner_private_key(owner=user, private_key=private_key)


def __decrypt_user_private_key(user):
    """Decrypt user private key."""
    if user.temporary_key and user.private_key and user.nonce:
        return __decrypt_with_aes(
            key=user.temporary_key,
            ciphertext=user.private_key,
            nonce=user.nonce,
            aad=b"private key for " + user.username.encode(),
        )
    exception = Exception("User keys are not properly setup!")
    flask.current_app.logger.exception(exception)
    raise exception


def __encrypt_invite_private_key(invite, private_key):
    """Encrypt invite private key."""
    return __encrypt_owner_private_key(owner=invite, private_key=private_key)


def __decrypt_invite_private_key(invite, temporary_key):
    """Decrypt invite private key."""
    if temporary_key and invite.private_key and invite.nonce:
        return __decrypt_with_aes(
            key=temporary_key,
            ciphertext=invite.private_key,
            nonce=invite.nonce,
            aad=b"private key for " + invite.email.encode(),
        )


def transfer_invite_private_key_to_user(invite, temporary_key, user):
    """Move private key associated to invite, to new user."""
    # Decrypt invite private key and encrypt it as new users private key
    private_key_bytes = __decrypt_invite_private_key(invite=invite, temporary_key=temporary_key)
    if private_key_bytes and isinstance(
        serialization.load_der_private_key(data=private_key_bytes, password=None),
        asymmetric.rsa.RSAPrivateKey,
    ):
        user.temporary_key = __encrypt_owner_private_key(
            owner=user, private_key=private_key_bytes, temporary_key=temporary_key
        )
        user.public_key = invite.public_key

        # Clean up sensitive information
        del private_key_bytes
        gc.collect()


def verify_invite_temporary_key(invite, temporary_key):
    """Verify the temporary key assigned to specific user invite."""
    private_key_bytes = __decrypt_invite_private_key(invite=invite, temporary_key=temporary_key)
    if private_key_bytes and isinstance(
        serialization.load_der_private_key(data=private_key_bytes, password=None),
        asymmetric.rsa.RSAPrivateKey,
    ):
        # Cleanup sensitive information
        del private_key_bytes
        gc.collect()
        return True
    return False


def __generate_rsa_key_pair(owner):
    """Generate new RSA Key Pair."""
    # Generate key and get keys as bytes
    private_key = asymmetric.rsa.generate_private_key(public_exponent=65537, key_size=4096)
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Set owners public key
    owner.public_key = public_key_bytes

    # Clean up sensitive information
    del private_key
    gc.collect()

    return private_key_bytes


def generate_user_key_pair(user):
    """Generate user key pair and encrypt private key."""
    private_key_bytes = __generate_rsa_key_pair(owner=user)
    __encrypt_user_private_key(user=user, private_key=private_key_bytes)

    # Clean up sensitive information
    del private_key_bytes
    gc.collect()


def generate_invite_key_pair(invite):
    """Generate key pair for invite and encrypt private key."""
    private_key_bytes = __generate_rsa_key_pair(owner=invite)
    temporary_key = __encrypt_invite_private_key(invite=invite, private_key=private_key_bytes)

    # Clean up sensitive information
    del private_key_bytes
    gc.collect()

    return temporary_key
