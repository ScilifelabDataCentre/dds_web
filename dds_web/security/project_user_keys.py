""" Code for generating and maintaining project and user related keys """

from cryptography.hazmat.primitives import asymmetric, serialization


def generate_user_key_pair():
    private_key = asymmetric.rsa.generate_private_key(public_exponent=65537, key_size=4096)
    return {
        "public_key": private_key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        ),
        "private_key": private_key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    }
