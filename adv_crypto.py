"""
adv_crypto.py - Minimal crypto helpers for LekhAI
=================================================

Provides:
- AES-256-GCM encryption/decryption for Aadhaar values
- Deterministic HMAC-based reference tokens

The pipeline stores only the token in the main records table. Encrypted
aadhaar values are returned to the caller for optional vault persistence.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv

load_dotenv(override=True)


def _get_secret_bytes() -> bytes:
    """
    Normalize ADV_ENCRYPTION_KEY into a stable 32-byte secret.

    We hash the configured secret so callers can provide a readable passphrase
    while AES-GCM still gets the required key length.
    """
    secret = os.getenv("ADV_ENCRYPTION_KEY", "").strip()
    if not secret:
        raise ValueError("ADV_ENCRYPTION_KEY is required")
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _validate_aadhaar(aadhaar: str) -> None:
    aadhaar = str(aadhaar or "").strip()
    if not aadhaar.isdigit() or len(aadhaar) != 12:
        raise ValueError(
            f"Could not extract valid 12-digit Aadhaar. Got: {aadhaar!r}"
        )


def encrypt_aadhaar(aadhaar: str) -> str:
    """
    Encrypt a 12-digit Aadhaar using AES-256-GCM and return base64 text.
    """
    _validate_aadhaar(aadhaar)
    key = _get_secret_bytes()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, aadhaar.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_aadhaar(vault_blob: str) -> str:
    """
    Reverse `encrypt_aadhaar`.
    """
    raw = base64.b64decode(vault_blob.encode("utf-8"))
    nonce = raw[:12]
    ciphertext = raw[12:]
    aesgcm = AESGCM(_get_secret_bytes())
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def _generate_reference_token(subject: str) -> str:
    """
    Generate a deterministic token for a privacy-safe subject string.
    """
    subject = str(subject or "").strip()
    if not subject:
        raise ValueError("Token source must not be empty")
    digest = hmac.new(
        key=_get_secret_bytes(),
        msg=subject.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"tok_{digest}"


def generate_reference_token(aadhaar: str) -> str:
    """
    Deterministic token for a valid Aadhaar number.
    """
    _validate_aadhaar(aadhaar)
    return _generate_reference_token(aadhaar)


def generate_subject_reference_token(subject: str) -> str:
    """
    Deterministic token for non-Aadhaar legacy identifiers such as ULPIN-based
    fallback subjects. The caller must pass a privacy-safe subject string.
    """
    return _generate_reference_token(subject)

