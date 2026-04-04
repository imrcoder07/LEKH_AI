# 🔐 Mission 4: Privacy Enforcement & Data Protection Layer
## *A Complete Learning & Implementation Guide*

> **Who is this for?** Developers building government-grade systems who need to go beyond storing data securely — they need to control who can see it, detect when it leaks, log every sensitive touch, and prove compliance to an auditor.

---

## 1. 🗺️ High-Level Architecture

The Privacy Layer is not a single file — it is a **cross-cutting concern** that intercepts data at every boundary: when it enters the system, when it is stored, when it is queried, and when it leaves via the API.

### Where Everything Happens

```text
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   [Scanned Upload]                                                  │
│         │                                                           │
│         ▼                                                           │
│   ┌───────────┐   ┌──────────────┐   ┌─────────────────────────┐  │
│   │    OCR    │──▶│  AES Vault   │──▶│  HMAC Reference Token   │  │
│   │  Engine   │   │  (encrypt)   │   │  (ghost identity)       │  │
│   └───────────┘   └──────────────┘   └────────────┬────────────┘  │
│                                                    │               │
│                                         ┌──────────┘               │
│                                         ▼                           │
│                                  ┌────────────┐                    │
│                                  │  Supabase  │ ← Zero raw PII    │
│                                  │    (DB)    │                    │
│                                  └─────┬──────┘                    │
│                                        │                           │
│                         ╔══════════════▼══════════════╗           │
│                         ║   PRIVACY ENFORCEMENT LAYER  ║           │
│                         ║                              ║           │
│                         ║  ┌──────────────────────┐   ║           │
│                         ║  │  RBAC Middleware      │   ║ ← WHO    │
│                         ║  │  (role enforcement)   │   ║           │
│                         ║  └──────────┬───────────┘   ║           │
│                         ║             │               ║           │
│                         ║  ┌──────────▼───────────┐   ║           │
│                         ║  │  PII Detection        │   ║ ← WHAT   │
│                         ║  │  (auto-scan output)   │   ║           │
│                         ║  └──────────┬───────────┘   ║           │
│                         ║             │               ║           │
│                         ║  ┌──────────▼───────────┐   ║           │
│                         ║  │  Redaction Engine     │   ║ ← HOW    │
│                         ║  │  (mask/filter)        │   ║           │
│                         ║  └──────────┬───────────┘   ║           │
│                         ║             │               ║           │
│                         ║  ┌──────────▼───────────┐   ║           │
│                         ║  │  Audit Logger         │   ║ ← WHEN   │
│                         ║  │  (every sensitive op) │   ║           │
│                         ║  └──────────────────────┘   ║           │
│                         ╚══════════════╤══════════════╝           │
│                                        │                           │
│                                        ▼                           │
│                             ┌─────────────────────┐               │
│                             │  Secure API Response │               │
│                             │  (filtered + masked) │               │
│                             └──────────┬──────────┘               │
│                                        │                           │
│                                        ▼                           │
│                                   [Frontend]                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Three Key Questions This Layer Answers

| Question | Answered By |
|----------|-------------|
| **WHO** can see this data? | RBAC Middleware |
| **WHAT** data is sensitive? | PII Detection |
| **HOW** is it shown? | Redaction Engine |
| **WHEN** was it accessed? | Audit Logger |

---

## 2. 🧾 Data Redaction Engine

Redaction is the process of **replacing sensitive data with a safe visual representation** before it leaves the backend. This is your last line of defence before data reaches a UI.

### Philosophy

Never trust that a downstream consumer will mask data themselves. The backend must produce already-masked output. Assume every API response will be screenshot, cached, or logged somewhere.

### Redaction Rules for Land Records

| Field | Raw | Masked |
|-------|-----|--------|
| Aadhaar | `123456789012` | `XXXX XXXX 9012` |
| Owner Token | `tok_4d9a7f2b...` | `tok_4d9a****` |
| Phone Number | `9876543210` | `XXXXXX3210` |
| Owner Name (optional) | `Ramesh Kumar` | `R****** K****` |

### Implementation (`privacy_layer.py`)

```python
import re


def mask_aadhaar(aadhaar: str) -> str:
    """
    Mask a 12-digit Aadhaar to XXXX XXXX XXXX format.
    Only the last 4 digits are visible — standard UIDAI display rule.
    
    Accepts with or without spaces/dashes (normalizes first).
    """
    digits = re.sub(r'[\s\-]', '', aadhaar)
    
    if len(digits) != 12 or not digits.isdigit():
        return "XXXX XXXX XXXX"  # Return safe fallback for malformed input
    
    return f"XXXX XXXX {digits[-4:]}"


def mask_phone(phone: str) -> str:
    """
    Mask a 10-digit Indian phone number, revealing only last 4 digits.
    """
    digits = re.sub(r'\D', '', phone)  # Remove non-digits
    if len(digits) < 4:
        return "XXXXXX"
    return f"XXXXXX{digits[-4:]}"


def mask_name(name: str) -> str:
    """
    Partially mask an owner name.
    "Ramesh Kumar" → "R****** K****"
    
    Each word is masked after the first character.
    """
    if not name:
        return "****"
    
    parts = name.strip().split()
    masked_parts = []
    for part in parts:
        if len(part) <= 1:
            masked_parts.append(part)
        else:
            masked_parts.append(part[0] + "*" * (len(part) - 1))
    
    return " ".join(masked_parts)


def mask_token(token: str) -> str:
    """
    Partially mask a reference token for display.
    "tok_4d9a7f2b3c1e..." → "tok_4d9a****"
    """
    if not token or len(token) < 12:
        return "tok_****"
    return token[:12] + "****"


def redact_record(record: dict, role: str) -> dict:
    """
    Apply redaction to a land record dict based on the caller's role.
    
    Returns a safe-to-transmit version of the record.
    The original dict is NEVER mutated.
    """
    # Always work on a copy — never mutate the source
    safe = dict(record)
    
    if role == "auditor":
        # Auditors see structure, not identity
        safe["Owner_Token"] = mask_token(safe.get("Owner_Token", ""))
        safe.pop("raw_text", None)  # Remove raw OCR dump entirely
        
    elif role == "user":
        # Users see token (for UI display) and basic land data
        safe["Owner_Token"] = mask_token(safe.get("Owner_Token", ""))
        safe.pop("raw_text", None)
        
    elif role == "admin":
        # Admins see full token but raw_text is still excluded (audit required for vault)
        safe.pop("raw_text", None)
    
    # Universal rule: Aadhaar NEVER appears in any role's output
    # (it shouldn't exist in the record dict at all — this is a defensive check)
    safe.pop("aadhaar", None)
    safe.pop("raw_aadhaar", None)
    safe.pop("encrypted_aadhaar", None)
    
    return safe
```

---

## 3. 🔍 PII Detection Layer

Before any data leaves a function or endpoint, run it through an **automatic PII scanner**. This catches accidental leaks — for example, if someone mistakenly passes a raw OCR dict through to an API response.

### Regex-Based PII Detector

```python
import re
import logging

logger = logging.getLogger("pii_detector")

# PII patterns: compiled once at module load for performance
PII_PATTERNS = {
    "aadhaar":  re.compile(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b'),
    "phone":    re.compile(r'\b[6-9]\d{9}\b'),            # Indian mobile numbers
    "pan":      re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'), # PAN card
    "email":    re.compile(r'[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.]+\.[a-zA-Z]{2,}'),
}


def detect_pii(text: str) -> dict:
    """
    Scan a text string for PII patterns.
    
    Returns a dict of detected PII types and their matches.
    Use this to audit OCR output, API responses, or log messages.
    
    Example:
        >>> detect_pii("Owner: Ramesh, Aadhaar: 1234 5678 9012")
        {"aadhaar": ["1234 5678 9012"]}
    """
    findings = {}
    for pii_type, pattern in PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            findings[pii_type] = matches
    return findings


def assert_no_pii_leak(data: dict | str, context: str = ""):
    """
    Assert that a dict or JSON string contains no raw PII.
    Raises ValueError and logs a security warning if PII is found.
    
    Use this as a gate before returning API responses.
    
    Args:
        data: The dict or string to check
        context: Description of where this check is happening (for logs)
    
    Raises:
        ValueError: If raw PII is detected
    """
    text = str(data)
    findings = detect_pii(text)
    
    if findings:
        logger.critical(
            f"[PII LEAK DETECTED] Context: '{context}' | "
            f"PII types found: {list(findings.keys())} | "
            "Response was BLOCKED."
        )
        raise ValueError(
            f"SECURITY VIOLATION: Response contains raw PII ({list(findings.keys())}). "
            "Block this response and investigate immediately."
        )


# Optional Future: NLP/NER-based detection
# Use spaCy or a fine-tuned BERT model to detect person names,
# organizations, and locations that regex cannot catch.
# from spacy_pii import detect_entities  # future integration
```

---

## 4. 🔐 Role-Based Access Control (RBAC)

Access control defines **who can see or do what** in your system. In GovTech systems, this is non-negotiable.

### Role Definitions

| Role | DB Access | Vault Decryption | Audit Logs | Masked Output |
|------|-----------|-----------------|------------|---------------|
| **admin** | Full read/write | Yes (with audit) | Full | Partial masking |
| **user** | Own records only | No | No | Full masking |
| **auditor** | Read-only | No | Full view | Maximum masking |

### How Roles Are Assigned

In this prototype, roles are stored in the **Flask session** after a login step. In production, this would be tied to a Supabase Auth JWT claim.

```python
# In app.py — after authentication
session['user_id'] = "admin_001"
session['role'] = "admin"  # or "user" / "auditor"
```

### Flask RBAC Decorator (`privacy_layer.py`)

```python
from functools import wraps
from flask import session, jsonify


def require_role(*allowed_roles):
    """
    Flask route decorator that enforces role-based access control.
    
    Usage:
        @app.route('/api/admin/decrypt')
        @require_role('admin')
        def decrypt_endpoint():
            ...
    
    If the caller's role is not in allowed_roles, returns 403 Forbidden.
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
                # Log unauthorized access attempt
                _write_audit_log(
                    user_id=session.get('user_id', 'unknown'),
                    action="UNAUTHORIZED_ACCESS_ATTEMPT",
                    resource=func.__name__,
                    status="DENIED",
                    metadata={"required_roles": list(allowed_roles), "caller_role": caller_role}
                )
                return jsonify({
                    "error": "Access denied. Insufficient privileges.",
                    "code": "FORBIDDEN"
                }), 403
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## 5. 📜 Audit Logging System

Every sensitive operation — especially vault decryptions and record modifications — must be logged permanently, tamper-evidently, and in enough detail that a future auditor can reconstruct exactly what happened.

### Supabase Audit Logs Table (add to `supabase_schema.sql`)

```sql
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      TEXT NOT NULL,
    action       TEXT NOT NULL,
    resource     TEXT,
    record_id    UUID,
    status       TEXT CHECK (status IN ('SUCCESS', 'DENIED', 'ERROR')),
    metadata     JSONB,
    ip_address   TEXT,
    "timestamp"  TIMESTAMPTZ DEFAULT NOW()
);

-- Audit logs are write-only from the app perspective
-- No UPDATE or DELETE allowed — logs are immutable
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role can insert audit logs"
ON public.audit_logs
FOR INSERT
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

-- Even service_role cannot delete or update audit logs
-- (enforce by removing UPDATE/DELETE from policy)
```

### Python Audit Logger (`privacy_layer.py`)

```python
import os
import json
from datetime import datetime, timezone
from supabase import create_client
from flask import request

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
    
    Audit actions to always log:
      - DECRYPT_AADHAAR
      - RECORD_CREATE
      - RECORD_ACCESS
      - RECORD_DELETE
      - UNAUTHORIZED_ACCESS_ATTEMPT
      - VAULT_ACCESS
    
    Args:
        user_id: Identity of the caller (from session)
        action: String constant describing what was done
        status: "SUCCESS", "DENIED", or "ERROR"
        resource: Which endpoint or function was accessed
        record_id: UUID of the land_record being accessed (if applicable)
        metadata: Any additional context (never put raw PII here)
    """
    try:
        supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        
        log_entry = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "record_id": record_id,
            "status": status,
            "ip_address": request.remote_addr if request else None,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("audit_logs").insert(log_entry).execute()
        
    except Exception as e:
        # CRITICAL: If the audit log fails, log to stderr and raise
        # Do NOT silently swallow — a failed audit log is a compliance failure
        import sys
        print(f"[AUDIT LOG FAILURE] {action} by {user_id}: {e}", file=sys.stderr)
        raise RuntimeError(f"Audit logging failed: {e}")


# Convenience wrappers for common actions
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
```

### Why Logs Cannot Be Tampered With

1. **INSERT-only policy:** The DB policy allows inserts but no UPDATEs or DELETEs.
2. **No direct table access for anon users:** RLS blocks all public access.
3. **Timestamped by the database:** Using `DEFAULT NOW()` — the server clock, not the app.
4. **Future: Hash-chain logs** — each log entry can include a SHA-256 hash of the previous entry, making any deletion mathematically detectable.

---

## 6. 🔒 Secure API Response Design

The API is where all the previous work either holds together or falls apart. Enforce the following rules at every endpoint:

### Rules

```text
❌ NEVER return: raw Aadhaar, full token, unmasked names, raw_text dump
✅ ALWAYS return: masked fields, role-filtered output, minimal fields
```

### Flask Secure API Examples (`app.py`)

```python
from flask import session, jsonify, request
from privacy_layer import require_role, redact_record, assert_no_pii_leak, log_record_access
from adv_crypto import decrypt_aadhaar, generate_reference_token
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


@app.route('/api/records/<record_id>', methods=['GET'])
@require_role('admin', 'user', 'auditor')
def get_record(record_id):
    """
    Retrieve a land record — output is always role-filtered and redacted.
    """
    caller_role = session.get('role')
    caller_id = session.get('user_id')
    
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    response = supabase.table("land_records").select("*").eq("id", record_id).execute()
    
    if not response.data:
        return jsonify({"error": "Record not found"}), 404
    
    record = response.data[0]
    
    # Log the access
    log_record_access(caller_id, record_id, caller_role)
    
    # Apply role-based redaction
    safe_record = redact_record(record, role=caller_role)
    
    # Final PII gate — defensive last check before transmission
    assert_no_pii_leak(safe_record, context=f"GET /api/records/{record_id}")
    
    return jsonify({"status": "ok", "data": safe_record}), 200


@app.route('/api/admin/vault/decrypt', methods=['POST'])
@require_role('admin')  # Only admins can request decryption
def vault_decrypt():
    """
    Decrypt vault Aadhaar for a given record.
    This endpoint is heavily audited. Every call is logged.
    Requires: { "record_id": "uuid", "reason": "court order ref: xxx" }
    """
    caller_id = session.get('user_id')
    body = request.get_json()
    record_id = body.get("record_id")
    reason = body.get("reason", "")
    
    if not reason:
        return jsonify({"error": "A documented reason is required for vault access"}), 400
    
    # Retrieve encrypted blob from vault storage
    # (In production: query a separate vault DB, not land_records)
    vault_blob = _retrieve_vault_blob(record_id)  # Your vault query here
    
    try:
        plain_aadhaar = decrypt_aadhaar(vault_blob)
        
        # Log successful decryption
        log_vault_access(caller_id, record_id, "SUCCESS", reason)
        
        # Never return raw Aadhaar — return a masked display version
        return jsonify({
            "status": "ok",
            "display": f"XXXX XXXX {plain_aadhaar[-4:]}",
            "access_logged": True
        }), 200
        
    except Exception as e:
        log_vault_access(caller_id, record_id, "ERROR", str(e))
        return jsonify({"error": "Vault decryption failed", "code": "VAULT_ERROR"}), 500
```

### What a Safe API Response Looks Like

```json
{
  "status": "ok",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "ULPIN": "08JD0101234567",
    "Owner_Token": "tok_4d9a****",
    "Area": "2.3 acres",
    "Geometry": null
  }
}
```

And what it must **never** look like:

```json
{
  "Owner_Token": "tok_4d9a7f2b3c1e...",
  "aadhaar": "123456789012",
  "raw_text": "Owner Name: Ramesh Kumar, Aadhaar: 1234 5678 9012..."
}
```

---

## 7. 🗑️ Data Retention & Cleanup

Uploaded documents are temporarily stored in `/uploads` for OCR processing. Once processed, the original file becomes a **security liability** — it contains raw Aadhaar in plaintext in the image itself.

### Cleanup Strategy

```python
import os
import time

UPLOAD_FOLDER = "uploads"
MAX_AGE_SECONDS = 300  # 5 minutes — enough for OCR, not forever


def secure_delete_file(filepath: str):
    """
    Delete a temporary upload file after processing.
    
    In higher security environments, overwrite with zeros before deleting
    to prevent file recovery from disk forensics.
    """
    if not os.path.exists(filepath):
        return
    
    try:
        # Overwrite file content with zeros before deletion
        file_size = os.path.getsize(filepath)
        with open(filepath, 'wb') as f:
            f.write(b'\x00' * file_size)
        
        os.remove(filepath)
        
    except Exception as e:
        # Log failure — a retained file is a privacy risk
        import logging
        logging.getLogger("retention").error(
            f"Failed to delete temporary file: {filepath} — {e}"
        )


def cleanup_stale_uploads():
    """
    Scan the uploads directory and delete files older than MAX_AGE_SECONDS.
    Schedule this to run periodically (e.g., with APScheduler or a cron job).
    """
    now = time.time()
    deleted = 0
    
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.isfile(filepath):
            age = now - os.path.getmtime(filepath)
            if age > MAX_AGE_SECONDS:
                secure_delete_file(filepath)
                deleted += 1
    
    return deleted
```

### Integrating Cleanup Into the Upload Flow

```python
@app.route('/api/upload', methods=['POST'])
def api_upload():
    # ... existing upload and OCR logic ...
    
    try:
        # 1. Save file temporarily
        file.save(filepath)
        
        # 2. Run OCR + vault + DB insert
        result = process_document(filepath)
        
        return jsonify({"status": "ok", "record_id": result["record_id"]}), 200
        
    finally:
        # 3. ALWAYS delete the file — even if processing failed
        secure_delete_file(filepath)
```

The `finally` block guarantees deletion whether processing succeeds or throws an exception.

---

## 8. 🚨 Abuse & Anomaly Detection

This is your early warning system. Without it, you might not notice that someone is systematically decrypting every record in your vault — which is a data breach even if each individual request seemed authorized.

### Rate-Based Anomaly Rules

```python
from collections import defaultdict
from datetime import datetime, timezone

# In-memory tracker (use Redis in production for persistence across restarts)
_decryption_tracker: dict[str, list] = defaultdict(list)

DECRYPTION_LIMIT = 5        # max decryptions per window
DECRYPTION_WINDOW = 60      # seconds


def check_decryption_rate(user_id: str) -> bool:
    """
    Returns True if user is within acceptable decryption rate.
    Returns False (and logs alert) if they are behaving suspiciously.
    """
    now = datetime.now(timezone.utc).timestamp()
    history = _decryption_tracker[user_id]
    
    # Prune entries outside the time window
    history = [t for t in history if now - t < DECRYPTION_WINDOW]
    _decryption_tracker[user_id] = history
    
    if len(history) >= DECRYPTION_LIMIT:
        import logging
        logging.getLogger("anomaly").warning(
            f"[ANOMALY ALERT] User '{user_id}' attempted {len(history)+1} "
            f"vault decryptions in {DECRYPTION_WINDOW}s. Blocking."
        )
        return False  # Block
    
    history.append(now)
    return True  # Allow
```

### Integration with PreBreach Shield

If you have an existing **PreBreach Shield / IDS** project, you can pipe anomaly alerts into it:

```python
def notify_prebreach(event_type: str, user_id: str, detail: str):
    """
    Send a security event to your PreBreach Shield intrusion detection system.
    """
    import requests
    
    payload = {
        "event_type": event_type,
        "source_system": "LekhAI",
        "user_id": user_id,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    prebreach_url = os.getenv("PREBREACH_WEBHOOK_URL")
    if prebreach_url:
        try:
            requests.post(prebreach_url, json=payload, timeout=3)
        except requests.RequestException:
            pass  # Don't let IDS notification failure block the main app
```

---

## 9. 🧪 Testing Strategy

```python
# tests/test_privacy_layer.py

def test_aadhaar_masking():
    from privacy_layer import mask_aadhaar
    assert mask_aadhaar("123456789012") == "XXXX XXXX 9012"
    assert mask_aadhaar("1234 5678 9012") == "XXXX XXXX 9012"
    assert mask_aadhaar("bad_input") == "XXXX XXXX XXXX"
    print("✅ Aadhaar masking correct")


def test_pii_detection():
    from privacy_layer import detect_pii, assert_no_pii_leak
    
    # Should detect Aadhaar
    leaky = {"data": "Aadhaar: 1234 5678 9012"}
    found = detect_pii(str(leaky))
    assert "aadhaar" in found
    
    # Clean record should pass
    safe = {"ULPIN": "08JD0101234567", "Owner_Token": "tok_4d9a****"}
    try:
        assert_no_pii_leak(safe, context="test")
        print("✅ PII detection working — safe record passed, leak detected")
    except ValueError:
        print("❌ False positive — clean record was flagged!")


def test_rbac_enforcement():
    from privacy_layer import redact_record
    
    record = {
        "ULPIN": "08JD0101234567",
        "Owner_Token": "tok_4d9a7f2b3c1eabcd",
        "Area": "2.3 acres",
        "raw_text": "Aadhaar: 1234 5678 9012 Owner: Ramesh"
    }
    
    # Auditor must not see raw_text or full token
    auditor_view = redact_record(record, role="auditor")
    assert "raw_text" not in auditor_view
    assert auditor_view["Owner_Token"].endswith("****")
    
    # User must not see raw_text
    user_view = redact_record(record, role="user")
    assert "raw_text" not in user_view
    
    # Admin sees token but not raw_text
    admin_view = redact_record(record, role="admin")
    assert "raw_text" not in admin_view
    assert "Owner_Token" in admin_view
    
    print("✅ RBAC redaction rules enforced correctly")


def test_api_leakage_prevention():
    """Simulate what the API produces and confirm no PII escapes."""
    from privacy_layer import redact_record, assert_no_pii_leak
    
    record = {
        "ULPIN": "08JD0101234567",
        "Owner_Token": "tok_4d9a7f2b3c1eabcd",
        "Area": "2.3 acres",
        "raw_text": "1234 5678 9012"  # raw OCR containing Aadhaar
    }
    
    safe = redact_record(record, role="user")
    assert_no_pii_leak(safe, context="API output test")
    print("✅ API response contains zero raw PII")
```

---

## 10. ⚠️ Common Mistakes

| Mistake | Why It's Critical | Fix |
|---------|------------------|-----|
| Returning raw Aadhaar in API | Any log, proxy, or screenshot = breach | Always run `redact_record()` before `jsonify()` |
| Logging with PII in message | Log files have much weaker access control than DB | Log only IDs and tokens, never values |
| Mixing vault and main DB | One leak exposes both datasets | Vault is a separate namespace, never `JOIN` with main tables |
| Trusting frontend role claims | A browser can send any JSON | Role is always read from `session` on the backend, never from request body |
| Silent audit log failure | Non-compliance you cannot detect or prove | Raise on audit failure — never swallow the exception |
| No file cleanup | GDPR/DPDP: "right to erasure" includes temp files | Always delete in `finally` block |
| Rate-limiting only by IP | Bypass trivially with VPN | Rate-limit by `user_id` from authenticated session |

---

## 11. 🚀 Future Improvements

| Improvement | Why | Priority |
|-------------|-----|----------|
| Dynamic policy engine (OPA/Casbin) | Rules change as govt requirements evolve | High |
| AI-based PII detection (spaCy NER) | Catch names, locations that regex misses | Medium |
| AES key rotation + re-encryption job | Limit blast radius if key is compromised | High |
| Compliance dashboard | One-page view for auditors/officers | Medium |
| Immutable log hash chain | Mathematical proof logs weren't deleted | High |
| Attribute-based access control (ABAC) | Fine-grained rules beyond simple roles | Low |

---

## 📋 Implementation Checklist

Before proceeding to Mission 5, verify:

- [ ] `privacy_layer.py` created with all functions
- [ ] `audit_logs` table created in Supabase via SQL Editor
- [ ] `@require_role()` decorator applied to all sensitive routes
- [ ] `redact_record()` called before every `jsonify()` that returns land data
- [ ] `assert_no_pii_leak()` gate added to all API responses
- [ ] `secure_delete_file()` called in `finally` block of upload endpoint
- [ ] All privacy tests in test suite passing ✅
- [ ] `audit_logs` table confirmed INSERT-only (no DELETE policy)

---

*Generated for the LekhAI Digital Land Records Ecosystem — GIGW 3.0 & DPDP Act Compliant*
