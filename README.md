# LekhAI | Digital Ledger Authority

![GIGW 3.0 Certified](https://img.shields.io/badge/GIGW_3.0-Certified-success)
![DPDP Act 2023](https://img.shields.io/badge/DPDP_Act-Compliant-blue)
![Flask](https://img.shields.io/badge/Backend-Flask-black)
![Supabase](https://img.shields.io/badge/Database-Supabase-green)

LekhAI is a lightweight, deployable digital land records ecosystem. It combines privacy-safe AI document processing, immutable cryptographic hashing, and officer-grade audit visibility into a single seamless workflow.

Designed for **Immutable Authority**, LekhAI strictly adheres to India's DPDP Act 2023, GIGW 3.0 accessibility guidelines, and the Indian Evidence Act Sec 65B.

---

## ✨ Core Features

*   **🛡️ DPDP-Aligned Record Processing:**
    *   **Ghost Identity (Tokenization):** Aadhaar numbers are tokenized immediately. The raw Aadhaar is stored securely in an AES-256 Vault, and only masked tokens (`tok_4d9a****`) enter the main database.
    *   **Explicit Consent:** User consent is strictly enforced before processing any document.
    *   **Secure Ephemeral Storage:** Uploaded files are overwritten and destroyed immediately after extraction to prevent forensic recovery.
*   **👁️ Immutable Ledger (Hash Chain):**
    *   Every successful record ingestion creates a verifiable SHA-256 hash block pointing to the previous entry, ensuring tamper-proof historical data.
    *   Real-time verification dashboard to audit the integrity of the chain.
*   **🔤 Hybrid AI OCR Pipeline:**
    *   Powered by `GEMMA-4-31b-it` Vision (via Google GenAI) for highly accurate English and Hindi field extraction (ULPIN, Area, Owner Name).
*   **📈 Performance Monitoring:**
    *   Built-in Prometheus exporter (`/metrics`) for tracking API latency, request volume, and HTTP error rates.
*   **⚖️ Evidence Act Sec 65B Ready:**
    *   Built-in legal module that generates digitally signed evidentiary certificates proving record integrity for judicial proceedings.
*   **🌐 Bilingual Experience:**
    *   GIGW 3.0 compliant, offering instant English and Hindi toggling across citizen-facing and officer-facing workflows.

---

## 🏗️ System Architecture

```text
[Scanned Upload] 
      ↓
[ Hybrid OCR ] → Extracts ULPIN, Aadhaar, Area
      ↓
[Privacy Gate] → Masks PII, Generates HMAC Ghost Token, Secures to AES Vault
      ↓
[Hash Ledger]  → Current Hash = SHA256(Record_Data + Previous_Hash)
      ↓
[ Supabase ]   → Stores Tokenized Data + Ledger Block
      ↓
[ Dashboard ]  → Live Tamper Verification & Sec 65B Output
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
* Python 3.9+
* A Supabase account (PostgreSQL)
* A Google GenAI API Key (for Gemma OCR)

### 2. Installation

Clone the repository and install dependencies:
```bash
git clone https://github.com/imrcoder07/Lekh_AI.git
cd Lekh_AI
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory and populate it with your credentials:

```ini
# Supabase Database Keys
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key

# AI / OCR Engine
GEMINI_API_KEY=your_google_genai_api_key
GEMMA_MODEL=gemini-1.5-flash  # Vision capable model

# Application Secrets
SECRET_KEY=your_flask_session_secret
```

### 4. Run the Application
```bash
python app.py
```
The application will be available at `http://127.0.0.1:5000/`.

---

## 📜 License
Proprietary / Government GovTech Prototype.