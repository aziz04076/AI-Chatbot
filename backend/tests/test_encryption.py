import pytest
import uuid
import sqlite3
from app.core.encryption import encryption_manager, ENC_PREFIX
from app.models.conversation import Conversation, Message
from app.core.database import AsyncSessionLocal, init_db
from app.config import settings

def test_encryption_roundtrip():
    samples = [
        "Simple plain text message",
        "Sensitive AWS Secret: AKIAIOSFODNN7EXAMPLE & wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "Multi-line YAML:\napiVersion: v1\nkind: Secret\ndata:\n  token: aGVsbG8=",
        "Unicode & Math: 🚀 NexusAI $\\sum_{i=1}^n x_i = \\int_0^1 f(t)dt$",
        ""
    ]
    for sample in samples:
        encrypted = encryption_manager.encrypt(sample)
        if sample:
            assert encrypted.startswith(ENC_PREFIX)
            assert encrypted != sample
        else:
            assert encrypted == ""
        decrypted = encryption_manager.decrypt(encrypted)
        assert decrypted == sample

def test_nonce_randomness_identical_plaintext():
    text = "Identical message text across sessions"
    enc1 = encryption_manager.encrypt(text)
    enc2 = encryption_manager.encrypt(text)

    # Different nonces produce different ciphertexts
    assert enc1 != enc2
    assert enc1.startswith(ENC_PREFIX)
    assert enc2.startswith(ENC_PREFIX)

    # Both decrypt to the original
    assert encryption_manager.decrypt(enc1) == text
    assert encryption_manager.decrypt(enc2) == text

def test_tamper_detection_fails_auth_tag():
    text = "Tamper detection test message"
    encrypted = encryption_manager.encrypt(text)
    # Corrupt characters in the middle of ciphertext
    prefix = ENC_PREFIX
    body = list(encrypted[len(prefix):])
    body[15] = "A" if body[15] != "A" else "B"
    tampered = prefix + "".join(body)

    with pytest.raises(ValueError) as exc:
        encryption_manager.decrypt(tampered)
    assert "decryption failed" in str(exc.value)

def test_backward_compatibility_legacy_plaintext():
    legacy_text = "Legacy message stored before encryption was enabled."
    # Strings without enc:v1: prefix pass through safely
    assert encryption_manager.decrypt(legacy_text) == legacy_text
    assert encryption_manager.is_encrypted(legacy_text) is False

@pytest.mark.asyncio
async def test_column_level_encryption_at_rest_in_sqlite():
    await init_db()

    conv_id = str(uuid.uuid4())
    msg_id = str(uuid.uuid4())
    secret_content = "CONFIDENTIAL_DB_PASSWORD_XYZ_9876543210"

    # 1. Insert message using SQLAlchemy ORM
    async with AsyncSessionLocal() as db:
        conv = Conversation(id=conv_id, title="Encrypted Test Session")
        db.add(conv)
        await db.flush()

        msg = Message(
            id=msg_id,
            conversation_id=conv_id,
            role="user",
            content=secret_content
        )
        db.add(msg)
        await db.commit()

    # 2. Inspect raw SQLite table directly bypassing ORM
    # Extract path to sqlite file
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM messages WHERE id = ?", (msg_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    raw_content_at_rest = row[0]

    # Verify at rest: content must be encrypted and plaintext MUST NOT exist
    assert raw_content_at_rest.startswith("enc:v1:")
    assert secret_content not in raw_content_at_rest

    # 3. Query via SQLAlchemy ORM: transparently decrypted
    async with AsyncSessionLocal() as db:
        loaded_msg = await db.get(Message, msg_id)
        assert loaded_msg is not None
        assert loaded_msg.content == secret_content
