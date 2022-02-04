""" Code for generating and maintaining project and user related keys """
import os

from cryptography.hazmat.primitives import asymmetric, ciphers, hashes, serialization
import gc


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


def encrypt_with_rsa(plaintext, public_key):
    """
    Encrypts the plaintext with the RSA algorithm using the public key
    :param plaintext: a byte string
    :param public_key: public key of the user
    """
    return public_key.encrypt(plaintext, __get_padding_for_rsa())


def decrypt_with_rsa(ciphertext, private_key):
    """
    Decrypts the ciphertext with the RSA algorithm using the private key
    :param ciphertext: encrypted content
    :param private_key: private key of the user
    """
    return private_key.decrypt(ciphertext, __get_padding_for_rsa())


def encrypt_project_private_key_for_user(user, project_private_key):
    return encrypt_with_rsa(project_private_key, user.public_key)


def generate_project_key_pair(user):
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
    encrypted_private_key = encrypt_project_private_key_for_user(user, private_key_bytes)

    del private_key_bytes
    del private_key
    gc.collect()

    return {
        "public_key": public_key_bytes.hex().upper(),
        "encrypted_private_key": encrypted_private_key,
    }


def encrypt_with_aes(key, plaintext, aad=None):
    """
    Encrypts the plaintext with the AES algorithm using the key
    :param key: symmetric key of the user
    :param plaintext: a byte string
    :param aad: Additional data that should be authenticated with the key, but is not encrypted. Can be None.
    """
    aesgcm = ciphers.aead.AESGCM(key)
    nonce = os.urandom(12)
    return {"nonce": nonce, "encrypted_key": aesgcm.encrypt(nonce, plaintext, aad)}


def decrypt_with_aes(key, ciphertext, nonce, aad=None):
    """
    Decrypts the ciphertext with the AES algorithm using the key
    :param key: symmetric key of the user
    :param ciphertext: encrypted content
    :param nonce: a unique value that has to be used only once to encrypt a given data with the given key
    :param aad: Additional data that should be authenticated with the key, but is not encrypted. Can be None.
    """
    aesgcm = ciphers.aead.AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, aad)


def encrypt_user_private_key(user, private_key):
    user.temporary_key = ciphers.aead.AESGCM.generate_key(bit_length=256)
    return encrypt_with_aes(
        user.temporary_key, private_key, aad=b"private key for user " + user.username.encode()
    )


def generate_user_key_pair(user):
    private_key = asymmetric.rsa.generate_private_key(public_exponent=65537, key_size=4096)
    private_key_bytes = private_key.private_bytes(
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    public_key_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    encrypted_private_key = encrypt_user_private_key(user, private_key_bytes)

    del private_key_bytes
    del private_key
    gc.collect()

    return {
        "public_key": public_key_bytes.hex().upper(),
        "encrypted_private_key": encrypted_private_key,
    }
