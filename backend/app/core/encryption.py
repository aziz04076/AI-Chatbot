import os
import base64
import logging
from typing import Optional, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from sqlalchemy import TypeDecorator, Text
from app.config import settings

logger = logging.getLogger("NexusAI-Encryption")

ENC_PREFIX = "enc:v1:"
HKDF_SALT = b"nexus-enterprise-aes-salt-2026"
HKDF_INFO = b"nexus-column-encryption-v1"

class EncryptionManager:
    """
    Enterprise-grade AES-256-GCM Column-Level Encryption Manager.
    - 256-bit key derived via HKDF-SHA256 from SECRET_KEY.
    - 96-bit (12-byte) cryptographically secure random Nonce per record write.
    - 128-bit authentication tag verification on read.
    - enc:v1: format with zero-breakage backward compatibility for legacy plaintext.
    """
    def __init__(self, secret_key: Optional[str] = None):
        raw_secret = (secret_key or settings.SECRET_KEY).encode("utf-8")
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=HKDF_SALT,
            info=HKDF_INFO,
        )
        self.derived_key = hkdf.derive(raw_secret)
        self.aesgcm = AESGCM(self.derived_key)

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        """
        Encrypts a plaintext string into authenticated AES-256-GCM ciphertext.
        Format: enc:v1:<base64(12-byte-nonce + ciphertext + 16-byte-auth-tag)>
        """
        if plaintext is None:
            return None
        if not isinstance(plaintext, str):
            plaintext = str(plaintext)
        if plaintext == "":
            return ""
        if plaintext.startswith(ENC_PREFIX):
            return plaintext

        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        encoded = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
        return f"{ENC_PREFIX}{encoded}"

    def decrypt(self, ciphertext_str: Optional[str]) -> Optional[str]:
        """
        Decrypts authenticated AES-256-GCM ciphertext back to plaintext string.
        Falls back to raw string if not starting with 'enc:v1:' (backward compatibility).
        """
        if ciphertext_str is None:
            return None
        if not isinstance(ciphertext_str, str):
            return ciphertext_str
        if ciphertext_str == "":
            return ""
        if not ciphertext_str.startswith(ENC_PREFIX):
            # Backward-compatible transparent pass-through for legacy unencrypted records
            return ciphertext_str

        encoded = ciphertext_str[len(ENC_PREFIX):]
        try:
            raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
            if len(raw) < 12:
                logger.warning("Ciphertext too short, returning as is.")
                return ciphertext_str
            nonce = raw[:12]
            payload = raw[12:]
            decrypted = self.aesgcm.decrypt(nonce, payload, None)
            return decrypted.decode("utf-8")
        except Exception as exc:
            logger.error(f"GCM authentication or decryption failed: {exc}")
            raise ValueError(f"AES-256-GCM decryption failed: Integrity check error or invalid key") from exc

    def is_encrypted(self, text: Any) -> bool:
        """Checks if a string is in enc:v1: ciphertext format."""
        return isinstance(text, str) and text.startswith(ENC_PREFIX)

encryption_manager = EncryptionManager()

class EncryptedColumn(TypeDecorator):
    """
    SQLAlchemy custom type that transparently encrypts data at rest using AES-256-GCM
    and decrypts on retrieval.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encryption_manager.encrypt(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return encryption_manager.decrypt(value)
