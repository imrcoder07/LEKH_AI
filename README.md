# 🏛️ LekhAI — Digital Ledger Authority

**Privacy-First AI System for Land Records in India**

!GIGW 3.0 Certified
!DPDP Act 2023
!Flask
!Supabase
!Status

---

## 🌍 Overview

**LekhAI** is a **privacy-first, AI-powered digital land record system** designed for India.

It transforms **paper-based land documents** into:

* 🔐 Secure digital records
* 🧾 Legally admissible evidence
* 🔗 Tamper-proof ledger entries

---

## 🧠 System Architecture (FAANG-Level)

> Clean, modular, production-ready architecture with strict privacy enforcement.

📌 **Recommended Diagram (Dark Theme for PPT & GitHub)**

!LekhAI Architecture

### 🔄 Core Flow

```
Upload → OCR → Extraction → Privacy → Hash → Database → Dashboard
```

### 🧩 Key Layers

* **Frontend** → Citizen & Officer dashboards
* **API Gateway** → Auth + Rate limiting
* **Backend (Flask)** → Orchestration layer
* **AI Layer** → OCR via external APIs (Gemma / HuggingFace)
* **Privacy Layer** → Aadhaar tokenization + AES vault
* **Integrity Layer** → SHA-256 hash chain
* **Data Layer** → PostgreSQL (Supabase + RLS)
* **Cache** → Redis for performance
* **Monitoring** → Logs + metrics

---

## 💡 Problem It Solves

India’s land record ecosystem suffers from:

* ❌ Forged / tampered documents
* ❌ Manual verification delays
* ❌ Privacy risks (Aadhaar exposure)
* ❌ Lack of audit transparency

👉 LekhAI introduces **trust, traceability, and automation**

---

## ✨ Key Features

### 🔐 Privacy-First Architecture

* Aadhaar is **never stored directly**
* Ghost tokenization
* AES-256 secure vault
* Consent-based processing

---

### 🤖 AI-Powered OCR

* Extracts structured fields (ULPIN, Owner, Area)
* Works on multilingual documents (Hindi + English)

---

### 🔗 Immutable Ledger

* SHA-256 hash chain
* Tamper detection
* Real-time verification

---

### ⚖️ Legal Compliance

* Section 65B certificate generation
* Court-ready digital evidence

---

## ⚙️ Tech Stack

| Layer      | Technology                  |
| ---------- | --------------------------- |
| Backend    | Flask                       |
| Database   | Supabase (PostgreSQL + RLS) |
| AI / OCR   | Gemini / HuggingFace APIs   |
| Security   | AES-256 + Tokenization      |
| Cache      | Redis                       |
| Deployment | Render / Docker             |

---

## 🚀 Quick Start

```bash
git clone https://github.com/imrcoder07/Lekh_AI.git
cd Lekh_AI
pip install -r requirements.txt
python app.py
```

---

## 🌐 Deployment (Render)

```bash
Build: pip install -r requirements.txt
Start: gunicorn app:app
```

---

## 📡 API Endpoints

### POST /api/upload

```json
{
  "status": "success",
  "data": {
    "ulpin": "...",
    "owner_token": "...",
    "area": "...",
    "hash": "..."
  }
}
```

### GET /api/verify

```json
{
  "status": "valid",
  "tampered": false
}
```

---

## 🎥 Demo

> Add a short walkthrough video (30–90s). This is the highest-impact section for reviewers.

* ▶️ **Watch Demo (YouTube/Loom)**: https://your-demo-link
* 🌐 **Live App (optional)**: https://your-live-url

**What to show in demo:**

1. Upload a sample land document
2. OCR extraction (ULPIN, Owner, Area)
3. Privacy masking (tokenized Aadhaar)
4. Hash generation + verification
5. Dashboard view (valid / tampered)

---

## 📸 Screenshots

> Store images under `/docs/screenshots/` and reference them below.

### 🖥️ Dashboard (Officer)

!Dashboard

### 📄 Upload & OCR Result

!Upload OCR

### 🔐 Privacy Layer (Tokenization)

!Privacy

### 🔗 Ledger Verification

!Ledger

---

## 🚀 Future Improvements

* Blockchain-based land registry (RWA)
* Offline OCR
* Mobile app for field officers
* Role-based dashboards

---

## 👨‍💻 Author

**Islam (imrcoder07)**
B.Tech CSE (IoT + Cybersecurity)

---

## � License

Proprietary — Academic Prototype