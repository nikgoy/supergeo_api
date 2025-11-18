"""
Tests for encryption service.

Tests Fernet encryption/decryption functionality.
"""
import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.services.encryption import EncryptionService, generate_fernet_key


class TestEncryptionService:
    """Test EncryptionService class."""

    def test_encrypt_decrypt_string(self):
        """Test encrypting and decrypting a string."""
        service = EncryptionService()
        plaintext = "secret-api-token-12345"

        # Encrypt
        encrypted = service.encrypt(plaintext)
        assert isinstance(encrypted, bytes)
        assert encrypted != plaintext.encode()

        # Decrypt
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_string_raises_error(self):
        """Test that encrypting empty string raises ValueError."""
        service = EncryptionService()

        with pytest.raises(ValueError, match="Cannot encrypt empty string"):
            service.encrypt("")

    def test_decrypt_empty_bytes_raises_error(self):
        """Test that decrypting empty bytes raises ValueError."""
        service = EncryptionService()

        with pytest.raises(ValueError, match="Cannot decrypt empty bytes"):
            service.decrypt(b"")

    def test_decrypt_invalid_token_raises_error(self):
        """Test that decrypting invalid token raises error."""
        service = EncryptionService()

        with pytest.raises(InvalidToken):
            service.decrypt(b"invalid-encrypted-data")

    def test_encrypt_optional_with_value(self):
        """Test encrypt_optional with a value."""
        service = EncryptionService()
        plaintext = "optional-secret"

        encrypted = service.encrypt_optional(plaintext)
        assert encrypted is not None
        assert isinstance(encrypted, bytes)

        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_optional_with_none(self):
        """Test encrypt_optional with None."""
        service = EncryptionService()

        encrypted = service.encrypt_optional(None)
        assert encrypted is None

    def test_decrypt_optional_with_value(self):
        """Test decrypt_optional with encrypted value."""
        service = EncryptionService()
        plaintext = "optional-secret"
        encrypted = service.encrypt(plaintext)

        decrypted = service.decrypt_optional(encrypted)
        assert decrypted == plaintext

    def test_decrypt_optional_with_none(self):
        """Test decrypt_optional with None."""
        service = EncryptionService()

        decrypted = service.decrypt_optional(None)
        assert decrypted is None

    def test_different_keys_cannot_decrypt(self):
        """Test that different keys cannot decrypt each other's data."""
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()

        service1 = EncryptionService(key1)
        service2 = EncryptionService(key2)

        plaintext = "secret-data"
        encrypted = service1.encrypt(plaintext)

        with pytest.raises(InvalidToken):
            service2.decrypt(encrypted)

    def test_unicode_string_encryption(self):
        """Test encrypting and decrypting unicode strings."""
        service = EncryptionService()
        plaintext = "测试数据 🔐 Тест données"

        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext

    def test_long_string_encryption(self):
        """Test encrypting and decrypting a long string."""
        service = EncryptionService()
        plaintext = "x" * 10000

        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext

    def test_special_characters_encryption(self):
        """Test encrypting strings with special characters."""
        service = EncryptionService()
        plaintext = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"

        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext


class TestGenerateFernetKey:
    """Test Fernet key generation."""

    def test_generate_key_returns_string(self):
        """Test that generate_fernet_key returns a string."""
        key = generate_fernet_key()
        assert isinstance(key, str)

    def test_generated_key_is_valid(self):
        """Test that generated key can be used with Fernet."""
        key = generate_fernet_key()

        # Should not raise an error
        fernet = Fernet(key.encode())

        # Should be able to encrypt/decrypt
        encrypted = fernet.encrypt(b"test")
        decrypted = fernet.decrypt(encrypted)
        assert decrypted == b"test"

    def test_generated_keys_are_unique(self):
        """Test that generated keys are unique."""
        keys = [generate_fernet_key() for _ in range(10)]
        assert len(set(keys)) == 10  # All unique

    def test_generated_key_length(self):
        """Test that generated key has correct length."""
        key = generate_fernet_key()
        # Fernet keys are 44 characters when base64 encoded
        assert len(key) == 44
