"""
privacy_layer.py — Privacy Enforcement Layer
=============================================
Implements Mission 4: Zero-exposure data handling.

  Ghost Aadhaar Principle: Aadhaar never leaves the Vault.
  Zero Trust Output:       All API responses are filtered and masked.
  Full Auditability:       Every sensitive action is logged to Supabase.

Usage:
    from privacy_layer import require_role, redact_record, assert_no_pii_leak
    from privacy_layer import log_vault_access, log_record_access, secure_delete_file
"""

import os
import re
import sys
import time
import logging
from functools import wraps
from datetime import datetime, timezone
from collections import defaultdict

from flask import session, jsonify, request
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("privacy_layer")
anomaly_logger = logging.getLogger("anomaly")

# ---------------------------------------------------------------------------
# PII Pattern Registry
# ---------------------------------------------------------------------------

PII_PATTERNS = {
    "aadhaar":  re.compile(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b'),
    "phone":    re.compile(r'\b[6-9]\d{9}\b'),
    "pan":      re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'),
    "email":    re.compile(r'[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.]+\.[a-zA-Z]{2,}'),
}

# ---------------------------------------------------------------------------
# Rate-limit Tracker (in-memory; use Redis in production)
# ---------------------------------------------------------------------------

_decryption_tracker: dict[str, list] = defaultdict(list)
DECRYPTION_LIMIT   = 5    # max requests
DECRYPTION_WINDOW  = 60   # seconds


# ===========================================================================
# SECTION 1: Data Redaction Engine
# ===========================================================================

def mask_aadhaar(aadhaar: str) -> str:
    """
    Mask a 12-digit Aadhaar to XXXX XXXX XXXX (last 4 visible).
    Standard UIDAI display rule.
    """
    digits = re.sub(r'[\s\-]', '', aadhaar)
    if len(digits) != 12 or not digits.isdigit():
        return "XXXX XXXX XXXX"
    return f"XXXX XXXX {digits[-4:]}"


def mask_phone(phone: str) -> str:
    """Mask a phone number, revealing only the last 4 digits."""
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 4:
        return "XXXXXX"
    return f"XXXXXX{digits[-4:]}"


def mask_name(name: str) -> str:
    """
    Partially mask an owner name.
    "Ramesh Kumar" → "R****** K****"
    """
    if not name:
        return "****"
    parts = name.strip().split()
    masked = [p[0] + "*" * (len(p) - 1) if len(p) > 1 else p for p in parts]
    return " ".join(masked)


def mask_token(token: str) -> str:
    """Show only the first 12 chars of a reference token."""
    if not token or len(token) < 12:
        return "tok_****"
    return token[:12] + "****"


def redact_record(record: dict, role: str) -> dict:
    """
    Apply role-based redaction to a land record dict.
    Returns a safe copy — the original is never mutated.

    Role rules:
      admin   → full token, no raw_text
      user    → masked token, no raw_text
      auditor → masked token, no raw_text, no Area
    """
    safe = dict(record)

    # Universal: strip anything that should never be in the main record
    for forbidden in ("aadhaar", "raw_aadhaar", "encrypted_aadhaar"):
        safe.pop(forbidden, None)

    # Always strip raw OCR text from API output
    safe.pop("raw_text", None)

    if role == "admin":
        pass  # Full token visible to admin

    elif role == "user":
        if "Owner_Token" in safe:
            safe["Owner_Token"] = mask_token(safe["Owner_Token"])

    elif role == "auditor":
        if "Owner_Token" in safe:
            safe["Owner_Token"] = mask_token(safe["Owner_Token"])
        safe.pop("Area", None)  # Auditors see structure, not property details

    return safe


# ===========================================================================
# SECTION 2: PII Detection
# ===========================================================================

def detect_pii(text: str) -> dict:
    """
    Scan a text string or dict-repr for PII patterns.
    Returns a dict of {pii_type: [matches]}.
    """
    findings = {}
    for pii_type, pattern in PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            findings[pii_type] = matches
    return findings


def assert_no_pii_leak(data, context: str = ""):
    """
    Assert that a response payload contains no raw PII.
    Raises ValueError and logs a CRITICAL alert if PII is found.

    Use as a gate before every jsonify() call on sensitive endpoints.
    """
    text = str(data)
    findings = detect_pii(text)
    if findings:
        logger.critical(
            f"[PII LEAK BLOCKED] Context: '{context}' | "
            f"PII detected: {list(findings.keys())}"
        )
        raise ValueError(
            f"SECURITY VIOLATION: Response contains raw PII "
            f"({list(findings.keys())}). Response blocked."
        )


# ===========================================================================
# SECTION 3: Role-Based Access Control
# ===========================================================================

def require_role(*allowed_roles):
    """
    Flask route decorator enforcing RBAC.

    Usage:
        @app.route('/api/records/<id>')
        @require_role('admin', 'user')
        def get_record(id): ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            caller_role = session.get('role')

            if not caller_role:
                return jsonify({
                    "error": "Authentication required",
                    "code": "UNAUTHENTICATED"
                }), 401

            if caller_role not in allowed_roles:
                _write_audit_log(
                    user_id=session.get('user_id', 'unknown'),
                    action="UNAUTHORIZED_ACCESS_ATTEMPT",
                    resource=func.__name__,
                    status="DENIED",
                    metadata={
                        "required_roles": list(allowed_roles),
                        "caller_role": caller_role
                    }
                )
                return jsonify({
                    "error": "Access denied. Insufficient privileges.",
                    "code": "FORBIDDEN"
                }), 403

            return func(*args, **kwargs)
        return wrapper
    return decorator


# ===========================================================================
# SECTION 4: Audit Logging
# ===========================================================================

def _write_audit_log(
    user_id: str,
    action: str,
    status: str = "SUCCESS",
    resource: str = None,
    record_id: str = None,
    metadata: dict = None
):
    """
    Write an immutable audit log entry to Supabase.
    Raises RuntimeError if logging fails (non-negotiable for compliance).

    Actions to log:
      RECORD_ACCESS, RECORD_CREATE, RECORD_DELETE,
      DECRYPT_AADHAAR, VAULT_ACCESS,
      UNAUTHORIZED_ACCESS_ATTEMPT
    """
    try:
        from supabase_utils import get_supabase_client
        supabase = get_supabase_client()

        ip = None
        try:
            ip = request.remote_addr
        except RuntimeError:
            pass  # Outside request context (e.g., tests)

        log_entry = {
            "user_id":   user_id,
            "action":    action,
            "resource":  resource,
            "record_id": record_id,
            "status":    status,
            "ip_address": ip,
            "metadata":  metadata or {},
        }

        supabase.table("audit_logs").insert(log_entry).execute()

    except Exception as e:
        print(f"[AUDIT LOG FAILURE] {action} by {user_id}: {e}", file=sys.stderr)
        raise RuntimeError(f"Audit logging failed — compliance breach: {e}")


def log_vault_access(user_id: str, record_id: str, status: str, reason: str = ""):
    _write_audit_log(
        user_id=user_id,
        action="DECRYPT_AADHAAR",
        status=status,
        resource="adv_crypto.decrypt_aadhaar",
        record_id=record_id,
        metadata={"reason": reason}
    )


def log_record_access(user_id: str, record_id: str, role: str):
    _write_audit_log(
        user_id=user_id,
        action="RECORD_ACCESS",
        status="SUCCESS",
        record_id=record_id,
        metadata={"role": role}
    )


# ===========================================================================
# SECTION 5: Anomaly Detection
# ===========================================================================

def check_decryption_rate(user_id: str) -> bool:
    """
    Rate-limit vault decryption requests per user.
    Returns False (and logs alert) if limit exceeded.
    """
    now = time.time()
    history = _decryption_tracker[user_id]

    # Prune expired entries
    history = [t for t in history if now - t < DECRYPTION_WINDOW]
    _decryption_tracker[user_id] = history

    if len(history) >= DECRYPTION_LIMIT:
        anomaly_logger.warning(
            f"[ANOMALY] User '{user_id}' attempted {len(history)+1} "
            f"vault decryptions in {DECRYPTION_WINDOW}s. Request BLOCKED."
        )
        _write_audit_log(
            user_id=user_id,
            action="RATE_LIMIT_BREACH",
            status="DENIED",
            resource="vault_decrypt",
            metadata={"attempts_in_window": len(history)}
        )
        return False

    history.append(now)
    return True


# ===========================================================================
# SECTION 6: Secure File Deletion
# ===========================================================================

UPLOAD_FOLDER  = "uploads"
MAX_AGE_SECONDS = 300  # 5 minutes


def secure_delete_file(filepath: str):
    """
    Overwrite file with zeros then delete.
    Prevents forensic recovery of temporary OCR upload files.
    """
    if not os.path.exists(filepath):
        return
    try:
        file_size = os.path.getsize(filepath)
        with open(filepath, 'wb') as f:
            f.write(b'\x00' * file_size)
        os.remove(filepath)
    except Exception as e:
        logging.getLogger("retention").error(
            f"Failed to securely delete: {filepath} — {e}"
        )


def cleanup_stale_uploads() -> int:
    """
    Delete upload files older than MAX_AGE_SECONDS.
    Call this from a scheduler (APScheduler, cron, or before each upload).
    Returns number of files deleted.
    """
    now = time.time()
    deleted = 0
    if not os.path.isdir(UPLOAD_FOLDER):
        return 0
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath) and (now - os.path.getmtime(filepath)) > MAX_AGE_SECONDS:
            secure_delete_file(filepath)
            deleted += 1
    return deleted


# ===========================================================================
# Self-test
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Privacy Layer Self-Test")
    print("=" * 60)

    # Test 1: Masking
    print("\n[1] Redaction Engine...")
    assert mask_aadhaar("123456789012") == "XXXX XXXX 9012"
    assert mask_aadhaar("1234 5678 9012") == "XXXX XXXX 9012"
    assert mask_aadhaar("bad") == "XXXX XXXX XXXX"
    assert mask_token("tok_4d9a7f2b3c1eabcd") == "tok_4d9a7f2b****"
    print("    ✅ Masking functions correct")

    # Test 2: PII Detection
    print("\n[2] PII Detection...")
    leaked = detect_pii("Owner Aadhaar: 1234 5678 9012, Phone: 9876543210")
    assert "aadhaar" in leaked
    assert "phone" in leaked
    clean = detect_pii("ULPIN: 08JD0101234567, Token: tok_4d9a****")
    assert not clean
    print("    ✅ PII detection working")

    # Test 3: Redaction by role
    print("\n[3] Role-based redaction...")
    record = {
        "ULPIN": "08JD0101234567",
        "Owner_Token": "tok_4d9a7f2b3c1eabcd",
        "Area": "2.3 acres",
        "raw_text": "Aadhaar 123456789012"
    }
    for role in ("admin", "user", "auditor"):
        safe = redact_record(record, role)
        assert "raw_text" not in safe, f"raw_text leaked for role {role}"
        assert "aadhaar" not in safe
    assert redact_record(record, "auditor").get("Owner_Token", "").endswith("****")
    print("    ✅ RBAC redaction rules enforced")

    # Test 4: PII leak gate
    print("\n[4] PII leak gate...")
    try:
        assert_no_pii_leak({"bad": "1234 5678 9012"}, context="test")
        print("    ❌ Gate failed to catch Aadhaar!")
    except ValueError:
        print("    ✅ PII gate correctly blocked leaky payload")

    print("\n" + "=" * 60)
    print("  All Privacy Layer tests passed.")
    print("=" * 60)
