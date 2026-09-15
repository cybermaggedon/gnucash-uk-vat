
import pytest

from gnucash_uk_vat.crypto import encrypt_response, decrypt_response


EMAIL = "user@example.com"
SECRET = "test-verification-secret"
PAYLOAD = {
    "access_token": "abc123",
    "refresh_token": "def456",
    "token_type": "bearer",
    "expires_in": 14400,
}


class TestRoundTrip:

    def test_encrypt_decrypt_round_trip(self):
        encrypted = encrypt_response(PAYLOAD, EMAIL, SECRET)
        assert "slug" in encrypted
        assert "encrypted" in encrypted
        assert "access_token" not in encrypted

        result = decrypt_response(encrypted, EMAIL, SECRET)
        assert result == PAYLOAD

    def test_each_encryption_is_unique(self):
        a = encrypt_response(PAYLOAD, EMAIL, SECRET)
        b = encrypt_response(PAYLOAD, EMAIL, SECRET)
        assert a["slug"] != b["slug"]
        assert a["encrypted"] != b["encrypted"]

    def test_decryption_recovers_all_fields(self):
        encrypted = encrypt_response(PAYLOAD, EMAIL, SECRET)
        result = decrypt_response(encrypted, EMAIL, SECRET)
        assert result["access_token"] == "abc123"
        assert result["refresh_token"] == "def456"
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == 14400


class TestDecryptionFailures:

    def test_wrong_email_fails(self):
        encrypted = encrypt_response(PAYLOAD, EMAIL, SECRET)
        with pytest.raises(Exception):
            decrypt_response(encrypted, "wrong@example.com", SECRET)

    def test_wrong_secret_fails(self):
        encrypted = encrypt_response(PAYLOAD, EMAIL, SECRET)
        with pytest.raises(Exception):
            decrypt_response(encrypted, EMAIL, "wrong-secret")

    def test_tampered_slug_fails(self):
        encrypted = encrypt_response(PAYLOAD, EMAIL, SECRET)
        encrypted["slug"] = "00" * 32
        with pytest.raises(Exception):
            decrypt_response(encrypted, EMAIL, SECRET)

    def test_tampered_ciphertext_fails(self):
        encrypted = encrypt_response(PAYLOAD, EMAIL, SECRET)
        encrypted["encrypted"] = "AAAA" + encrypted["encrypted"][4:]
        with pytest.raises(Exception):
            decrypt_response(encrypted, EMAIL, SECRET)


class TestResponseFormat:

    def test_slug_is_hex_string(self):
        encrypted = encrypt_response(PAYLOAD, EMAIL, SECRET)
        slug = encrypted["slug"]
        assert isinstance(slug, str)
        assert len(slug) == 64
        bytes.fromhex(slug)

    def test_encrypted_is_base64_string(self):
        encrypted = encrypt_response(PAYLOAD, EMAIL, SECRET)
        import base64
        decoded = base64.b64decode(encrypted["encrypted"])
        assert len(decoded) > 44
