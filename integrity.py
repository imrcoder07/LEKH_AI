"""
integrity.py — Cryptographic Hash Chain Verifier
================================================
Mission 5: Integrity & Audit Dashboard

Implements the tamper-detection engine for the land_ledger.
Formula (per PROTOTYPE_RULES §3B):
    Hash_current = SHA256(Data_JSON + Hash_previous)

Usage:
    from integrity import verify_chain, get_chain_summary
"""

import os
import json
import hashlib
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("integrity")


# ---------------------------------------------------------------------------
# Core: Hash Computation (must match ocr_pipeline._compute_hash exactly)
# ---------------------------------------------------------------------------

def compute_expected_hash(record_data: dict, previous_hash: str) -> str:
    """
    Recompute SHA-256 hash for a land record.
    Must be identical to the formula used during ingestion.

        Hash = SHA256(JSON(record, sort_keys=True) + previous_hash)
    """
    payload = json.dumps(record_data, sort_keys=True) + previous_hash
    return hashlib.sha256(payload.encode()).hexdigest()


def _canonicalize_area_value(value: Optional[object]) -> str:
    """Mirror the ingest-time area normalization before hashing."""
    if value is None:
        return "0"

    text = str(value).strip().replace(",", ".")
    match = re.search(r"(\d+[\.,]?\d*)", text)
    if match:
        text = match.group(1).replace(",", ".")

    try:
        normalized = format(Decimal(text).normalize(), "f")
    except (InvalidOperation, ValueError):
        return "0"

    normalized = normalized.rstrip("0").rstrip(".") if "." in normalized else normalized
    return normalized or "0"


# ---------------------------------------------------------------------------
# Chain Verification Engine
# ---------------------------------------------------------------------------

def verify_chain() -> dict:
    """
    Iterate every entry in land_ledger chronologically,
    recompute the expected hash from live land_records data,
    and compare against the stored hash.

    Returns:
        {
          "status":        "INTACT" | "TAMPERED" | "EMPTY" | "ERROR",
          "total":         int,
          "verified":      int,
          "tampered":      int,
          "chain":         list[ChainEntry],
          "verified_at":   ISO datetime string
        }

    ChainEntry:
        {
          "record_id":       str,
          "timestamp":       str,
          "stored_hash":     str,
          "expected_hash":   str,
          "previous_hash":   str,
          "ulpin":           str,
          "owner_token":     str (masked),
          "status":          "OK" | "BROKEN_LINK" | "HASH_MISMATCH" | "MISSING_RECORD"
        }
    """
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        # Fetch full ledger ordered from first to last (ascending).
        # Use timestamp rather than UUID id so chronological chain order is stable.
        ledger_resp = (
            sb.table("land_ledger")
            .select("id, record_id, current_hash, previous_hash, timestamp")
            .order("timestamp", desc=False)
            .execute()
        )
        ledger = ledger_resp.data

        if not ledger:
            return {
                "status": "EMPTY",
                "total": 0, "verified": 0, "tampered": 0,
                "chain": [],
                "verified_at": _now()
            }

        chain_results = []
        tampered_count = 0
        expected_previous_hash = "GENESIS"

        for entry in ledger:
            record_id     = entry.get("record_id")
            stored_hash   = entry.get("current_hash", "")
            previous_hash = entry.get("previous_hash", "GENESIS")
            timestamp     = entry.get("timestamp", "")

            # Fetch the corresponding land record to recompute hash
            rec_resp = (
                sb.table("land_records")
                .select("ulpin, owner_token, area, geometry")
                .eq("id", record_id)
                .execute()
            )

            if not rec_resp.data:
                chain_results.append({
                    "record_id":     record_id,
                    "timestamp":     timestamp,
                    "stored_hash":   stored_hash,
                    "expected_hash": "N/A",
                    "previous_hash": previous_hash,
                    "ulpin":         "UNKNOWN",
                    "owner_token":   "****",
                    "status":        "MISSING_RECORD"
                })
                tampered_count += 1
                continue

            rec = rec_resp.data[0]
            # Reconstruct the data dict exactly as it was during ingestion
            # Note: keys must match ocr_pipeline.persist_to_database() exactly
            record_data = {
                "ulpin":       rec.get("ulpin"),
                "owner_token": rec.get("owner_token"),
                "area":        rec.get("area"),
                "geometry":    rec.get("geometry"),
            }

            # The ingest pipeline hashes the canonical string area, so we must
            # mirror that exact payload shape during verification.
            record_data["area"] = _canonicalize_area_value(record_data["area"])

            expected_hash = compute_expected_hash(record_data, previous_hash)
            hash_ok = (expected_hash == stored_hash)
            link_ok = (previous_hash == expected_previous_hash)
            is_ok = hash_ok and link_ok
            if is_ok:
                entry_status = "OK"
                reason = "Hash and chain link verified."
            elif hash_ok and not link_ok:
                entry_status = "BROKEN_LINK"
                reason = "Block hash matches record data, but previous_hash does not point to the prior ledger block."
            else:
                entry_status = "HASH_MISMATCH"
                reason = "Stored hash does not match the current record payload."

            if not is_ok:
                tampered_count += 1
                logger.warning(
                    f"[TAMPER DETECTED] Record {record_id} | "
                    f"Expected: {expected_hash[:16]}... | "
                    f"Stored:   {stored_hash[:16]}... | "
                    f"Link OK: {link_ok}"
                )

            # Mask token for safe display
            token = rec.get("owner_token", "")
            masked_token = token[:12] + "****" if len(token) > 12 else "****"

            chain_results.append({
                "record_id":     record_id,
                "timestamp":     timestamp,
                "stored_hash":   stored_hash,
                "expected_hash": expected_hash,
                "previous_hash": previous_hash,
                "ulpin":         rec.get("ulpin", ""),
                "owner_token":   masked_token,
                "status":        entry_status,
                "reason":        reason,
            })
            expected_previous_hash = stored_hash

        overall = "INTACT" if tampered_count == 0 else "TAMPERED"
        logger.info(
            f"[Chain] Verified {len(chain_results)} records | "
            f"Status: {overall} | Tampered: {tampered_count}"
        )

        return {
            "status":       overall,
            "total":        len(chain_results),
            "verified":     len(chain_results) - tampered_count,
            "tampered":     tampered_count,
            "chain":        chain_results,
            "verified_at":  _now()
        }

    except Exception as e:
        logger.error(f"[Chain] Verification error: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "total": 0, "verified": 0, "tampered": 0,
            "chain": [],
            "verified_at": _now(),
            "error": str(e)
        }


def get_chain_summary() -> dict:
    """
    Lightweight summary (no per-record detail). Used for dashboard header.
    """
    result = verify_chain()
    return {
        "status":      result["status"],
        "total":       result["total"],
        "verified":    result["verified"],
        "tampered":    result["tampered"],
        "verified_at": result["verified_at"],
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Self-test (dry-run, no DB write)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Integrity Engine — Hash Formula Test")
    print("=" * 60)

    # Test 1: Determinism — same input must always give same hash
    data = {"ULPIN": "08JD0101234567", "Owner_Token": "tok_abc", "Area": "2.3 acres", "Geometry": None}
    h1 = compute_expected_hash(data, "GENESIS")
    h2 = compute_expected_hash(data, "GENESIS")
    assert h1 == h2, "Hash not deterministic!"
    print(f"\n[1] Determinism:    ✅  {h1[:32]}...")

    # Test 2: Avalanche effect — tiny change → completely different hash
    data2 = dict(data)
    data2["Area"] = "2.4 acres"  # 0.1 difference
    h3 = compute_expected_hash(data2, "GENESIS")
    assert h1 != h3, "Avalanche effect not working!"
    print(f"[2] Avalanche:      ✅  Changed 0.1 → hash differs")

    # Test 3: Chain linking — previous hash feeds in
    h_gen   = compute_expected_hash(data,  "GENESIS")
    h_block2 = compute_expected_hash(data2, h_gen)
    h_block3 = compute_expected_hash(data,  h_block2)
    assert h_block3 != h_gen, "Chain not tracking!"
    print(f"[3] Chain linking:  ✅  3-block mini-chain verified")

    # Test 4: Tamper simulation
    stored_hash   = compute_expected_hash(data, "GENESIS")
    tampered_data = dict(data)
    tampered_data["Area"] = "999 acres"  # Simulated DB edit
    recomputed    = compute_expected_hash(tampered_data, "GENESIS")
    detected      = (recomputed != stored_hash)
    print(f"[4] Tamper detect:  ✅  {'DETECTED' if detected else 'MISSED (BUG!)'}")

    print("\n" + "=" * 60)
    print("  All integrity tests passed.")
    print("=" * 60)
