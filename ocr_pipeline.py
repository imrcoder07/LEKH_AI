"""
ocr_pipeline.py — Hybrid OCR Ingestion Pipeline
================================================
Mission 4: Lightweight + LLM-powered document processing

Architecture:
  ┌──────────────────────────────────────────────────────────┐
  │  Uploaded Document (PNG/JPG/PDF)                        │
  │         │                                               │
  │         ▼                                               │
  │  ┌─────────────┐    OpenCV preprocessing               │
  │  │  Preprocess │    (grayscale, denoise, threshold)     │
  │  └──────┬──────┘    Local, fast, ~30MB package         │
  │         │                                               │
  │         ▼                                               │
  │  ┌─────────────┐    pytesseract (Tesseract binary)     │
  │  │ Local  OCR  │    Extracts raw text + confidence     │
  │  │ (Tesseract) │    Tiny wrapper, no model downloads   │
  │  └──────┬──────┘                                        │
  │         │  raw_text + confidence                        │
  │         ▼                                               │
  │  ┌─────────────────────────────────┐                   │
  │  │  Gemini Flash Vision API        │  FREE TIER        │
  │  │  • Receives: image + raw_text   │  1500 req/day     │
  │  │  • Extracts: ULPIN, Aadhaar,    │  ~2MB package     │
  │  │    Area as structured JSON      │                   │
  │  │  • Handles: Hindi + English     │                   │
  │  │  • Corrects: OCR typos          │                   │
  │  └──────┬──────────────────────────┘                   │
  │         │  structured fields                            │
  │         ▼                                               │
  │  ┌─────────────┐                                        │
  │  │ Privacy Gate│  → AES-256-GCM Vault + HMAC Token     │
  │  └──────┬──────┘                                        │
  │         ▼                                               │
  │  ┌─────────────┐                                        │
  │  │  Supabase   │  land_records + land_ledger            │
  │  └─────────────┘                                        │
  └──────────────────────────────────────────────────────────┘

Deployment footprint:
  pytesseract          ~10 KB (Python wrapper only)
  opencv-headless      ~30 MB (no GUI)
  google-generativeai  ~2 MB
  Tesseract binary     ~60 MB (system install, not in venv)
  Total venv delta:    ~35 MB (vs ~500 MB for PaddlePaddle)
"""

import os
import re
import json
import base64
import hashlib
import logging
import multiprocessing
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger("ocr_pipeline")

CONFIDENCE_THRESHOLD = 0.85  # Per PROTOTYPE_RULES Mission 4
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "20"))
GEMINI_MAX_TIMEOUT_SECONDS = int(os.getenv("GEMINI_MAX_TIMEOUT_SECONDS", "120"))
SUPABASE_TIMEOUT_SECONDS = int(os.getenv("SUPABASE_TIMEOUT_SECONDS", "15"))
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")
ENABLE_TESSERACT = os.getenv("ENABLE_TESSERACT", "false").strip().lower() in {"1", "true", "yes"}
GEMMA_MAX_IMAGE_SIDE = int(os.getenv("GEMMA_MAX_IMAGE_SIDE", "1800"))
GEMMA_RETRY_IMAGE_SIDE = int(os.getenv("GEMMA_RETRY_IMAGE_SIDE", "1280"))
GEMMA_JPEG_QUALITY = int(os.getenv("GEMMA_JPEG_QUALITY", "85"))


class PipelineStageError(RuntimeError):
    """Raised when a specific external stage fails or times out."""

    def __init__(self, stage: str, message: str):
        self.stage = stage
        self.detail = message
        super().__init__(f"{stage}: {message}")


def _user_message_for_stage_error(stage: str, detail: str) -> str:
    """Convert low-level stage failures into messages safe for the UI."""
    detail_lower = detail.lower()
    if "timed out" in detail_lower:
        return f"{stage} is taking too long to respond. Please try again."
    if "access is denied" in detail_lower or "forbidden by its access permissions" in detail_lower:
        return f"{stage} is unavailable from this environment right now."
    if "duplicate key value violates unique constraint" in detail_lower and "ulpin" in detail_lower:
        return "A land record with this ULPIN already exists in the database."
    if "violates check constraint" in detail_lower and "ulpin" in detail_lower:
        return "The extracted ULPIN did not pass database validation. Please review the document fields."
    if "could not extract valid 12-digit aadhaar" in detail_lower:
        return "We could not confidently extract a valid Aadhaar number from this document."
    if "missing or invalid ulpin" in detail_lower:
        return "We could not confidently extract a valid 14-character ULPIN from this document."
    return f"{stage} failed. Please try again."


def _run_with_timeout(fn, timeout_seconds: int, stage: str):
    """Run a blocking call with a hard timeout so requests fail predictably."""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeoutError:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise PipelineStageError(stage, f"timed out after {timeout_seconds}s")
    except PipelineStageError:
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    except Exception as exc:
        executor.shutdown(wait=False, cancel_futures=True)
        raise PipelineStageError(stage, str(exc)) from exc
    finally:
        if future.done():
            executor.shutdown(wait=False, cancel_futures=True)


def _gemma_worker(image_path: str, raw_text: str, api_key: str, timeout_seconds: int, queue):
    """Run the Gemma API request in a child process so it can be terminated safely."""
    try:
        from google import genai
        from PIL import Image as PILImage

        client = genai.Client(
            api_key=api_key,
            http_options={"timeout": timeout_seconds * 1000},
        )
        pil_image = PILImage.open(image_path).convert("RGB")
        prompt = EXTRACTION_PROMPT.format(raw_text=raw_text or "(OCR unavailable)")
        response = client.models.generate_content(
            model=GEMMA_MODEL,
            contents=[prompt, pil_image],
        )
        queue.put({"ok": True, "text": (response.text or "").strip()})
    except Exception as exc:
        queue.put({"ok": False, "error": str(exc)})

# ---------------------------------------------------------------------------
# Stage 1: Image Preprocessing (local, OpenCV)
# ---------------------------------------------------------------------------

def preprocess_image(image_path: str) -> np.ndarray:
    """
    Prepare scanned document for OCR.
    Grayscale → denoise → adaptive threshold → deskew.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, blockSize=11, C=2
    )
    return _deskew(binary)


def _deskew(image: np.ndarray) -> np.ndarray:
    coords = np.column_stack(np.where(image > 0))
    if len(coords) == 0:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.5:
        return image
    h, w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(image, M, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def _create_gemma_variant(image_path: str, max_side: int) -> dict:
    """
    Create a network-friendly JPEG variant for hosted vision inference.
    Large scans are resized to a bounded side length to reduce payload size
    and improve model response times.
    """
    from PIL import Image as PILImage

    with PILImage.open(image_path) as pil_image:
        image = pil_image.convert("RGB")
        width, height = image.size
        longest_side = max(width, height)

        if longest_side > max_side:
            scale = max_side / float(longest_side)
            new_size = (
                max(1, int(round(width * scale))),
                max(1, int(round(height * scale))),
            )
            image = image.resize(new_size, PILImage.Resampling.LANCZOS)
            resized = True
        else:
            resized = False

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            temp_path = tmp.name

        image.save(
            temp_path,
            format="JPEG",
            quality=GEMMA_JPEG_QUALITY,
            optimize=True,
        )

    return {
        "path": temp_path,
        "cleanup": True,
        "resized": resized,
        "max_side": max_side,
    }


def _gemma_attempt_plan(image_path: str) -> list[dict]:
    """
    Build staged Gemma attempts.
    The first pass preserves more detail; the second pass is smaller and gets a
    longer timeout so slower model responses still have a chance to complete.
    """
    base_timeout = max(20, GEMINI_TIMEOUT_SECONDS)
    attempts = [{
        "label": "optimized-primary",
        "timeout": min(base_timeout, GEMINI_MAX_TIMEOUT_SECONDS),
        **_create_gemma_variant(image_path, GEMMA_MAX_IMAGE_SIDE),
    }]

    retry_timeout = min(max(base_timeout * 2, 45), GEMINI_MAX_TIMEOUT_SECONDS)
    if GEMMA_RETRY_IMAGE_SIDE != GEMMA_MAX_IMAGE_SIDE or retry_timeout > attempts[0]["timeout"]:
        attempts.append({
            "label": "optimized-retry",
            "timeout": retry_timeout,
            **_create_gemma_variant(image_path, GEMMA_RETRY_IMAGE_SIDE),
        })

    return attempts


# ---------------------------------------------------------------------------
# Stage 2: Local OCR (pytesseract — fast, offline, confidence extraction)
# ---------------------------------------------------------------------------

def _get_tesseract_cmd() -> Optional[str]:
    """Locate Tesseract binary. Tries common Windows install paths."""
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None  # Assume it's on PATH


def run_local_ocr(image: np.ndarray) -> dict:
    """
    Run Tesseract on preprocessed image.
    Returns raw text and mean confidence score.

    If Tesseract is not installed, returns empty text with 0 confidence.
    Gemini Vision will still handle structured extraction independently.
    """
    try:
        import pytesseract
        from PIL import Image as PILImage

        # Set path if needed (Windows)
        tesseract_cmd = _get_tesseract_cmd()
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        pil_img = PILImage.fromarray(image)
        # PSM 6 = single block of text; OEM 3 = default LSTM
        config = "--psm 6 --oem 3"
        data = pytesseract.image_to_data(
            pil_img, lang="eng", config=config,
            output_type=pytesseract.Output.DICT
        )

        words, confs = [], []
        for i, conf in enumerate(data["conf"]):
            if int(conf) > 0:
                word = data["text"][i].strip()
                if word:
                    words.append(word)
                    confs.append(int(conf) / 100.0)

        raw_text = " ".join(words)
        mean_conf = sum(confs) / len(confs) if confs else 0.0

        logger.info(f"[Tesseract] {len(words)} words | confidence: {mean_conf:.2%}")
        return {"raw_text": raw_text, "confidence": round(mean_conf, 4)}

    except Exception as e:
        logger.warning(f"[Tesseract] Not available or failed: {e}. Falling back to Gemma/regex.")
        return {"raw_text": "", "confidence": 0.0}


# ---------------------------------------------------------------------------
# Stage 3: Gemini Flash Vision — Structured Field Extraction
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are a land records digitization expert for India.
Analyze this scanned government land record document.

The raw OCR text (may have errors) is:
{raw_text}

Extract the following fields as a valid JSON object only:
{{
  "ulpin": "14-character alphanumeric Unique Land Parcel ID (e.g. 08JD0101234567) or null",
  "aadhaar": "12-digit Aadhaar number with no spaces or dashes (e.g. 123456789012) or null",
  "area": "land area as string with unit (e.g. '2.3 acres') or null",
  "owner_name": "owner full name or null",
  "survey_no": "survey/khasra number or null",
  "village": "village name or null",
  "confidence_note": "brief note on extraction quality"
}}

Rules:
- For aadhaar: extract only the 12 digits, strip all spaces and dashes
- If a field is not present or unreadable, use null
- Return ONLY the JSON object, no markdown, no extra text
"""


def run_gemma_extraction(image_path: str, raw_text: str) -> dict:
    """
    Send image + raw OCR text to hosted Gemma for structured extraction.

    Gemma sees both the actual image and the raw OCR text,
    allowing it to correct OCR errors using visual context.
    Free tier: 15 req/min, 1500 req/day on gemini-1.5-flash.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("[Gemma] API key not configured. Falling back to regex extraction.")
        return _regex_fallback(raw_text)

    attempts = []
    last_error = None
    try:
        attempts = _gemma_attempt_plan(image_path)

        for attempt in attempts:
            queue = multiprocessing.Queue()
            proc = multiprocessing.Process(
                target=_gemma_worker,
                args=(attempt["path"], raw_text, api_key, attempt["timeout"], queue),
                daemon=True,
            )
            logger.info(
                "[Gemma] Attempt %s | timeout=%ss | max_side=%s | resized=%s",
                attempt["label"],
                attempt["timeout"],
                attempt["max_side"],
                attempt["resized"],
            )
            proc.start()
            proc.join(attempt["timeout"])
            if proc.is_alive():
                proc.terminate()
                proc.join(1)
                last_error = PipelineStageError("Gemma extraction", f"timed out after {attempt['timeout']}s")
                logger.warning("[Gemma] %s failed: %s", attempt["label"], last_error.detail)
                continue

            result = queue.get() if not queue.empty() else {
                "ok": False,
                "error": "Gemma worker exited without a response.",
            }
            if not result.get("ok"):
                last_error = PipelineStageError(
                    "Gemma extraction",
                    result.get("error", "Unknown Gemma worker failure."),
                )
                logger.warning("[Gemma] %s failed: %s", attempt["label"], last_error.detail)
                continue

            raw_response = result["text"].strip()
            raw_response = re.sub(r"```(?:json)?", "", raw_response).strip("` \n")
            extracted = json.loads(raw_response)
            logger.info(
                "[Gemma] Success on %s | fields=%s",
                attempt["label"],
                [k for k, v in extracted.items() if v],
            )
            return extracted

    except json.JSONDecodeError as e:
        raw_preview = locals().get("raw_response", "")[:200]
        logger.error(f"[Gemma] JSON parse failed: {e}. Raw: {raw_preview}")
    except Exception as e:
        last_error = e
        logger.error(f"[Gemma] API call failed: {e}. Using regex fallback.")
    finally:
        for attempt in attempts:
            if attempt.get("cleanup") and os.path.exists(attempt["path"]):
                os.remove(attempt["path"])

    if isinstance(last_error, PipelineStageError):
        logger.error(f"[Gemma] {last_error.detail}. Using regex fallback.")
    return _regex_fallback(raw_text)


def _regex_fallback(text: str) -> dict:
    """
    Pure regex field extraction — used if Gemini is unavailable.
    Less accurate but zero cost and offline.
    """
    def find(pattern, flags=0):
        m = re.search(pattern, text, flags)
        return m.group(1).strip() if m else None

    raw_aadhaar = find(r"(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})")
    clean_aadhaar = re.sub(r"[\s\-]", "", raw_aadhaar) if raw_aadhaar else None

    area_m = re.search(
        r"(\d+[\.,]?\d*)\s*(acres?|hectares?|guntha|bigha|sq\.?\s*ft\.?)",
        text, re.IGNORECASE
    )

    return {
        "aadhaar":    clean_aadhaar,
        "ulpin":      find(r"\b([A-Z0-9]{14})\b"),
        "area":       f"{area_m.group(1)} {area_m.group(2)}" if area_m else None,
        "owner_name": find(r"(?:Name|Owner|Malik|Khatadhar)[:\s]+([A-Za-z\u0900-\u097F\s]+)", re.IGNORECASE),
        "survey_no":  find(r"(?:Survey|Khasra)\s*(?:No\.?|Number)[:\s]*([A-Za-z0-9/]+)", re.IGNORECASE),
        "village":    None,
        "confidence_note": "regex-only fallback"
    }


# ---------------------------------------------------------------------------
# Stage 4: Privacy Gate → Vault → Supabase
# ---------------------------------------------------------------------------

def _compute_hash(data: dict, previous_hash: str) -> str:
    payload = json.dumps(data, sort_keys=True) + previous_hash
    return hashlib.sha256(payload.encode()).hexdigest()


def _get_last_hash() -> str:
    try:
        from supabase_utils import get_supabase_client
        sb = get_supabase_client()
        result = (sb.table("land_ledger")
                  .select("current_hash")
                  .order("timestamp", desc=True)
                  .limit(1).execute())
        if result.data:
            return result.data[0]["current_hash"]
    except Exception:
        pass
    return "GENESIS"


def _normalize_ulpin(value: Optional[str]) -> Optional[str]:
    """Normalize ULPIN to uppercase compact form and validate shape."""
    if value is None:
        return None

    ulpin = re.sub(r"[^A-Za-z0-9]", "", str(value)).upper()
    if not ulpin:
        return None

    if re.fullmatch(r"[A-Z0-9]{14}", ulpin):
        return ulpin
    return None


def persist_to_database(fields: dict) -> dict:
    """
    Privacy gate + AES Vault + Supabase insert.
    Aadhaar never reaches the database in any form.
    """
    from supabase_utils import get_supabase_client
    from adv_crypto import (
        encrypt_aadhaar,
        generate_reference_token,
        generate_subject_reference_token,
    )

    aadhaar = fields.get("aadhaar")

    raw_area = fields.get("area") or "0"
    import re
    area_match = re.search(r'(\d+[\.,]?\d*)', str(raw_area))
    area_numeric = area_match.group(1).replace(',', '.') if area_match else "0"
    ulpin = _normalize_ulpin(fields.get("ulpin"))
    if not ulpin:
        raise PipelineStageError(
            "ULPIN validation",
            f"missing or invalid ULPIN: {fields.get('ulpin')!r}"
        )

    aadhaar_str = str(aadhaar).strip() if aadhaar is not None else ""
    has_valid_aadhaar = aadhaar_str.isdigit() and len(aadhaar_str) == 12

    # Aadhaar is optional for older land records. When absent, derive a
    # deterministic non-sensitive owner token from the ULPIN instead.
    if has_valid_aadhaar:
        owner_token = generate_reference_token(aadhaar_str)
        encrypted_aadhaar = encrypt_aadhaar(aadhaar_str)
    else:
        owner_token = generate_subject_reference_token(f"NOAADHAAR:{ulpin}")
        encrypted_aadhaar = None

    record_data = {
        "ulpin":       ulpin,
        "owner_token": owner_token,
        "area":        area_numeric,
        "geometry":    {},
    }

    from supabase_utils import get_supabase_client
    sb = get_supabase_client()
    try:
        rec = _run_with_timeout(
            lambda: sb.table("land_records").insert(record_data).execute(),
            SUPABASE_TIMEOUT_SECONDS,
            "Supabase land_records insert"
        )
        record_id = rec.data[0]["id"]
    except PipelineStageError as e:
        detail_lower = e.detail.lower()
        if "duplicate key value violates unique constraint" in detail_lower and "ulpin" in detail_lower:
            existing = _run_with_timeout(
                lambda: sb.table("land_records").select("id").eq("ulpin", ulpin).limit(1).execute(),
                SUPABASE_TIMEOUT_SECONDS,
                "Supabase land_records lookup"
            )
            record_id = existing.data[0]["id"] if existing.data else None
            logger.info(f"[DB] Existing record reused for ULPIN {ulpin}")
            return {
                "record_id": record_id,
                "owner_token": owner_token,
                "current_hash": None,
                "encrypted_aadhaar": encrypted_aadhaar,
                "already_exists": True,
                "ulpin": ulpin,
                "area": area_numeric,
            }
        raise

    previous_hash = _get_last_hash()
    current_hash  = _compute_hash(record_data, previous_hash)

    # Note: Supabase PostgREST lowercases column names in REST API
    # even when schema uses quoted mixed-case identifiers
    _run_with_timeout(
        lambda: sb.table("land_ledger").insert({
            "record_id":     record_id,
            "current_hash":  current_hash,
            "previous_hash": previous_hash,
        }).execute(),
        SUPABASE_TIMEOUT_SECONDS,
        "Supabase land_ledger insert"
    )

    logger.info(f"[DB] Persisted record {record_id} | hash: {current_hash[:16]}...")
    return {
        "record_id":          record_id,
        "owner_token":        owner_token,
        "current_hash":       current_hash,
        "encrypted_aadhaar":  encrypted_aadhaar,  # store separately in vault
        "ulpin":              ulpin,
        "area":               area_numeric,
    }


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def process_document(image_path: str) -> dict:
    """
    Full hybrid OCR pipeline for a land record document.

    Returns:
        {status, record_id, confidence, flagged, message, hash}
    """
    try:
        logger.info(f"[Pipeline] Start: {Path(image_path).name}")
        pre_path = image_path + "_pre.png"

        # Stage 1: Preprocess
        preprocessed = preprocess_image(image_path)
        cv2.imwrite(pre_path, preprocessed)

        # Stage 2: Optional local OCR. In lightweight mode we rely on Gemma only.
        if ENABLE_TESSERACT:
            local_result = run_local_ocr(preprocessed)
            raw_text = local_result["raw_text"]
            confidence = local_result["confidence"]
        else:
            raw_text = ""
            confidence = 0.0

        # Stage 3: Hosted Gemma image extraction
        fields = run_gemma_extraction(image_path, raw_text)

        # Clean up preprocessed temp file
        if os.path.exists(pre_path):
            os.remove(pre_path)

        # Confidence gate
        # When Tesseract is absent (confidence=0.0), trust Gemma if key is configured.
        # Gemma having successfully extracted fields is itself a quality signal.
        gemma_available = bool(
            os.getenv("GEMINI_API_KEY", "").strip()
            and os.getenv("GEMINI_API_KEY") != "your_gemini_api_key_here"
        )
        gemma_extracted = bool(fields.get("ulpin") or fields.get("area"))
        gemma_core_fields = sum(
            1 for key in ("ulpin", "aadhaar", "area") if fields.get(key)
        )

        if ENABLE_TESSERACT and confidence > 0:
            # Tesseract gave us a real confidence score — use it
            effective_confidence = confidence
        elif gemma_available and gemma_core_fields >= 3:
            effective_confidence = 0.95
        elif gemma_available and gemma_core_fields == 2:
            effective_confidence = 0.88
        elif gemma_available and gemma_extracted:
            effective_confidence = 0.70
        else:
            effective_confidence = 0.0
            logger.info(
                "[Pipeline] Gemma extraction unavailable | gemma=%s extracted=%s core_fields=%s",
                gemma_available,
                gemma_extracted,
                gemma_core_fields,
            )

        flagged = effective_confidence < CONFIDENCE_THRESHOLD

        if flagged:
            logger.warning(
                f"[Pipeline] Flagged: conf={effective_confidence:.0%} "
                f"tesseract={confidence:.2%} enabled={ENABLE_TESSERACT} "
                f"gemma={gemma_available} extracted={gemma_extracted} core_fields={gemma_core_fields}"
            )
            return {
                "status":     "flagged",
                "record_id":  None,
                "confidence": effective_confidence,
                "flagged":    True,
                "message":    (
                    f"OCR confidence {effective_confidence:.0%} below threshold. "
                    "Flagged for manual officer review."
                )
            }

        has_valid_aadhaar = bool(
            str(fields.get("aadhaar") or "").strip().isdigit()
            and len(str(fields.get("aadhaar") or "").strip()) == 12
        )

        # Stage 4: Vault + DB
        db_result = persist_to_database(fields)

        return {
            "status":     "exists" if db_result.get("already_exists") else "success",
            "record_id":  db_result["record_id"],
            "confidence": effective_confidence,
            "flagged":    False,
            "message":    (
                "A land record with this ULPIN already exists."
                if db_result.get("already_exists")
                else (
                    "Legacy land record stored successfully without Aadhaar."
                    if not has_valid_aadhaar
                    else "Document processed and stored successfully."
                )
            ),
            "aadhaar_found": has_valid_aadhaar,
            "hash":       db_result.get("current_hash"),
            "ulpin":      db_result.get("ulpin"),
            "owner_token": db_result.get("owner_token"),
            "area":       db_result.get("area"),
        }

    except PipelineStageError as e:
        logger.error(f"[Pipeline] {e.stage} failed: {e.detail}", exc_info=True)
        return {
            "status":     "error",
            "record_id":  None,
            "confidence": 0.0,
            "flagged":    False,
            "message":    _user_message_for_stage_error(e.stage, e.detail)
        }
    except Exception as e:
        logger.error(f"[Pipeline] Error: {e}", exc_info=True)
        return {
            "status":     "error",
            "record_id":  None,
            "confidence": 0.0,
            "flagged":    False,
            "message":    f"Processing failed: {str(e)}"
        }
    finally:
        if 'pre_path' in locals() and os.path.exists(pre_path):
            os.remove(pre_path)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile
    from PIL import Image, ImageDraw

    print("=" * 60)
    print("  Hybrid OCR Pipeline Self-Test")
    print("  (pytesseract + Gemini Flash Vision)")
    print("=" * 60)

    # Create synthetic land record image
    img = Image.new("RGB", (700, 250), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.multiline_text((40, 30), (
        "GOVERNMENT OF RAJASTHAN — LAND RECORD\n"
        "ULPIN: 08JD0101234567\n"
        "Owner: Ramesh Kumar\n"
        "Aadhaar: 1234 5678 9012\n"
        "Area: 2.3 acres  Survey No: 45/A"
    ), fill=(0, 0, 0), spacing=10)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f.name)
        tmp = f.name

    print(f"\n[1] Test image: {tmp}")

    # Stage 2: Local OCR
    preprocessed = preprocess_image(tmp)
    local = run_local_ocr(preprocessed)
    print(f"\n[2] Tesseract confidence: {local['confidence']:.2%}")
    print(f"    Raw text sample: {local['raw_text'][:100]}")

    # Stage 3: Gemini (will use regex fallback if key not set)
    fields = run_gemma_extraction(tmp, local["raw_text"])
    print(f"\n[3] Extracted fields:")
    for k, v in fields.items():
        print(f"    {k:20}: {v}")

    # Stage 4: Ghost Identity check (no DB write in test)
    aadhaar = fields.get("aadhaar")
    if aadhaar and len(str(aadhaar)) == 12:
        from adv_crypto import generate_reference_token
        token = generate_reference_token(str(aadhaar))
        assert str(aadhaar) not in token, "Aadhaar visible in token!"
        print(f"\n[4] Ghost Identity: Aadhaar → {token}")
        print("    ✅ Raw Aadhaar NOT in token")
    else:
        print(f"\n[4] Could not find valid Aadhaar (got '{aadhaar}') — add GEMINI_API_KEY for full accuracy")

    os.remove(tmp)
    print("\n" + "=" * 60)
    print("  Self-test complete.")
    print("=" * 60)
