# 📜 PROTOTYPE_RULES.md (Final – Claude-Orchestrated Antigravity Blueprint v2)

This document is the **single source of truth** for the
**Integrated Digital Land Records Ecosystem**.

It defines **system behavior, agent orchestration, and execution rules**.

---

# 1. 🎯 Project Mission & Identity

**Objective:**
Build a lightweight, deployable land registry prototype that ensures:

* Document integrity (tamper-proof records)
* Privacy compliance (DPDP Act, Aadhaar rules)
* Multilingual accessibility (GIGW 3.0)
* Legal admissibility (Indian Evidence Act Sec 65B)

within a **one-week controlled sprint**.

---

# 2. ⚠️ Global Constraints (STRICT)

* Max **8GB RAM**
* Heavy processing via Hugging Face APIs
* No raw sensitive data storage
* Must be:

  * Lightweight
  * Modular
  * API-driven
  * Deployable
* Strict schema compliance

---

# 3. 🏗️ System Architecture

* Frontend: Google Stitch
* Backend: Flask
* Database: Supabase (PostgreSQL + RLS)
* OCR: PaddleOCR-VL (HF API)
* Hashing: SHA256

---

# 4. 🔄 System Data Flow

```text
Upload → OCR → Extraction
→ Privacy → Hash → Database
→ Ledger → API → UI
```

---

# 5. 🧩 Core Modules

## OCR Module

* Input: Image
* Output: JSON + confidence

## Extraction Module

* ULPIN, Owner, Area, Geometry

## Privacy Module

* Tokenization (vault.py)
* Masking

## Ledger Module

```
Hash_current = SHA256(Data_JSON + Hash_previous)
```

## Legal Module

* Sec 65B PDF generation

---

# 6. 🔐 Privacy & Security

* ADV mandatory
* Consent modal required
* Masking enforced
* No sensitive logs

---

# 7. 📡 API Contract

## POST /api/upload

```json
{
  "file": "<image>"
}
```

Response:

```json
{
  "status": "success",
  "data": {
    "ulpin": "...",
    "owner_token": "...",
    "area": "...",
    "confidence": 0.91,
    "hash": "..."
  }
}
```

---

## GET /api/verify

```json
{
  "status": "valid",
  "tampered": false
}
```

---

# 8. 🗄️ Database Schema

### land_records

* ulpin
* owner_token
* area
* geometry

### land_ledger

* record_id
* current_hash
* previous_hash
* timestamp

---

# 9. ⚠️ Failure Handling

* OCR < 0.85 → REVIEW_REQUIRED
* DB failure → retry once
* Hash mismatch → tampering
* No Aadhaar exposure

---

# 10. 🔐 Security Boundaries

* Tokenize before DB
* Mask before response
* No raw OCR storage
* Hash before storage

---

# 11. 🌐 Multilingual

* English/Hindi toggle
* Affects UI + OCR

---

# 12. 🚀 Execution Mode

* STRICT mode
* No assumptions
* Mission order enforced

---

# 13. ✅ Definition of Done

* API works
* Data secure
* Privacy enforced
* UI validated

---

# 14. 📋 Missions

1. Scaffolding
2. Database
3. Privacy
4. OCR
5. Ledger
6. Legal

---

# 15. 🔑 Environment Variables

```
SUPABASE_URL=
SUPABASE_KEY=
HF_API_KEY=
SECRET_KEY=
```

---

# 16. 📊 Logging

* Log API + hash
* No sensitive data

---

# 🧠 17. Lead Agent — Claude

### Role:

Central orchestrator

### Responsibilities:

* Read document
* Select mission
* Break into tasks
* Assign agents
* Validate outputs

### Rules:

* No direct implementation
* Must delegate
* Enforce constraints

---

# 🤖 18. Domain-Specific Agents (UPDATED)

---

## ⚙️ API Agent

* Handles Flask backend
* Implements endpoints
* Integrates all modules

---

## 🔤 OCR Agent

* Handles GEMMA-4-31b-it API
* Returns structured output
* Applies confidence scoring

---

## 🔐 Privacy Agent

* Aadhaar tokenization (ADV)
* Data masking
* Prevents sensitive leakage

---

## 🧮 Ledger Agent

* Generates hashes
* Maintains chain integrity
* Detects tampering

---

## 🗄️ Data Agent

* Handles Supabase operations
* Enforces RLS
* Validates data before storage

---

## 🎨 UI Agent

* Uses Stitch MCP
* Builds UI
* Handles bilingual logic

---

## 🛡️ Security Agent

* Uses Snyk MCP
* Scans vulnerabilities

---

## 📋 Task Agent

* Uses Linear MCP
* Tracks progress

---

# 19. 🔄 Agent Execution Flow

```text
Claude
 ↓
Task Agent → create tasks
 ↓
API Agent → backend
 ↓
OCR Agent → extraction
 ↓
Privacy Agent → masking
 ↓
Ledger Agent → hashing
 ↓
Data Agent → DB storage
 ↓
UI Agent → frontend
 ↓
Security Agent → scan
 ↓
Claude → validate → next mission
```

---

# 20. ⚙️ Agent Invocation Rules

* Claude always initiates
* Each agent = single responsibility
* No cross-domain execution
* MCP tools used only via assigned agents

---

# 🚀 FINAL DIRECTIVE

All agents must:

* Follow this document strictly
* Produce deterministic outputs
* Maintain privacy compliance
* Avoid assumptions

---

# 🎯 END GOAL

Deliver a **deployable, privacy-first, legally compliant land record system**
with verifiable integrity and modular architecture.
