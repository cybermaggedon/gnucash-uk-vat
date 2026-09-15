
import os
import json
import base64
import hmac
import hashlib

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey, X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def _derive_private_key(slug_bytes, verification_secret, email):
    seed = hmac.new(
        slug_bytes + verification_secret.encode(),
        email.encode(),
        hashlib.sha256,
    ).digest()
    return X25519PrivateKey.from_private_bytes(seed)


def _derive_symmetric_key(shared_secret):
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"",
    ).derive(shared_secret)


def encrypt_response(payload, email, verification_secret):
    slug = os.urandom(32)
    private_key = _derive_private_key(slug, verification_secret, email)
    public_key = private_key.public_key()

    ephemeral_key = X25519PrivateKey.generate()
    shared = ephemeral_key.exchange(public_key)
    symmetric_key = _derive_symmetric_key(shared)

    nonce = os.urandom(12)
    plaintext = json.dumps(payload).encode()
    ciphertext = ChaCha20Poly1305(symmetric_key).encrypt(nonce, plaintext, None)

    ephemeral_pub_bytes = ephemeral_key.public_key().public_bytes_raw()
    encrypted = ephemeral_pub_bytes + nonce + ciphertext

    return {
        "slug": slug.hex(),
        "encrypted": base64.b64encode(encrypted).decode(),
    }


def decrypt_response(response_json, email, verification_secret):
    slug = bytes.fromhex(response_json["slug"])
    encrypted = base64.b64decode(response_json["encrypted"])

    private_key = _derive_private_key(slug, verification_secret, email)

    ephemeral_pub = X25519PublicKey.from_public_bytes(encrypted[:32])
    nonce = encrypted[32:44]
    ciphertext = encrypted[44:]

    shared = private_key.exchange(ephemeral_pub)
    symmetric_key = _derive_symmetric_key(shared)

    plaintext = ChaCha20Poly1305(symmetric_key).decrypt(nonce, ciphertext, None)
    return json.loads(plaintext)
