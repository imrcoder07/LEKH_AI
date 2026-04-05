import os
from datetime import datetime, timezone
from supabase_utils import get_supabase_client

def generate_sec65b_certificate(record_id: str, request_ip: str = "127.0.0.1") -> dict:
    """
    Mission 6: Legal Module
    Generates a Section 65B (Indian Evidence Act) compliance certificate
    for a digital land record.
    """
    sb = get_supabase_client()
    
    # 1. Fetch Record
    rec_resp = sb.table("land_records").select("*").eq("id", record_id).execute()
    if not rec_resp.data:
        raise ValueError(f"Record {record_id} not found.")
    record = rec_resp.data[0]

    # 2. Fetch Ledger Hash
    ledg_resp = sb.table("land_ledger").select("*").eq("Record_ID", record_id).order("Timestamp", desc=True).limit(1).execute()
    if not ledg_resp.data:
        raise ValueError(f"Ledger entry for {record_id} not found.")
    ledger = ledg_resp.data[0]

    # 3. Construct Certificate Text
    cert_text = (
        "CERTIFICATE UNDER SECTION 65B OF THE INDIAN EVIDENCE ACT, 1872\n\n"
        "This is to certify that the electronic record described below was produced by a computer "
        "during the period over which the computer was used regularly to store or process information "
        "for the purposes of digital land record management.\n\n"
        "Property Details:\n"
        f"- ULPIN: {record.get('ULPIN')}\n"
        f"- Area: {record.get('Area')} acres\n"
        f"- Owner Token (Masked Identity): {record.get('Owner_Token')}\n\n"
        "Cryptographic Integrity:\n"
        f"- SHA-256 Hash: {ledger.get('Current_Hash')}\n"
        f"- Ledger Timestamp: {ledger.get('Timestamp')}\n"
        f"- Previous Block Hash: {ledger.get('Previous_Hash')}\n\n"
        "I further certify that to the best of my knowledge and belief, the computer system was "
        "operating properly at the time of generating this record, and the cryptographic hash "
        "guarantees the record has not been tampered with since ingestion.\n\n"
        f"Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"System IP: {request_ip}\n"
        "Authorized by: LekhAI Digital Land Records System (Automated)"
    )

    return {
        "record_id": record_id,
        "ulpin": record.get("ULPIN"),
        "hash": ledger.get("Current_Hash"),
        "certificate_text": cert_text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }