"""
Encryption service for sensitive client data.

Uses Fernet symmetric encryption for encrypting Cloudflare credentials
and other sensitive data at rest in the database.
"""
from typing import Optional
from cryptography.fernet import Fernet
from app.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, key: Optional[str] = None):
        """
        Initialize the encryption service.

        Args:
            key: Fernet key as base64-encoded string. If None, uses settings.fernet_key
        """
        key_to_use = key or settings.fernet_key
        self._fernet = Fernet(key_to_use.encode())

    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Encrypted bytes

        Raises:
            ValueError: If plaintext is empty
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")

        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        """
        Decrypt ciphertext bytes to a string.

        Args:
            ciphertext: The encrypted bytes

        Returns:
            Decrypted string

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty bytes")

        decrypted = self._fernet.decrypt(ciphertext)
        return decrypted.decode()

    def encrypt_optional(self, plaintext: Optional[str]) -> Optional[bytes]:
        """
        Encrypt a string if it's not None, otherwise return None.

        Args:
            plaintext: The string to encrypt or None

        Returns:
            Encrypted bytes or None
        """
        if plaintext is None:
            return None
        return self.encrypt(plaintext)

    def decrypt_optional(self, ciphertext: Optional[bytes]) -> Optional[str]:
        """
        Decrypt bytes if not None, otherwise return None.

        Args:
            ciphertext: The encrypted bytes or None

        Returns:
            Decrypted string or None
        """
        if ciphertext is None:
            return None
        return self.decrypt(ciphertext)


# Global encryption service instance
encryption_service = EncryptionService()


def generate_fernet_key() -> str:
    """
    Generate a new Fernet key.

    Returns:
        Base64-encoded Fernet key as string

    Usage:
        >>> key = generate_fernet_key()
        >>> print(f"FERNET_KEY={key}")
    """
    return Fernet.generate_key().decode()
