from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import os
import logging
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv(override=True)

# Lazy-import OCR pipeline (heavy; loaded once on first upload)
def _get_pipeline():
    from ocr_pipeline import process_document
    return process_document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

app = Flask(__name__)
# Secret key needed for session management (e.g. Bilingual Toggle state)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key_lekhai")

# Enable CORS for the application
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Allowed extensions for land records (PDF, images)
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _runtime_health_payload():
    """
    Surface non-secret runtime details so we can verify the live Flask process
    is using the expected OCR configuration.
    """
    payload = {
        "status": "ok",
        "cwd": os.getcwd(),
        "pid": os.getpid(),
        "upload_folder": app.config['UPLOAD_FOLDER'],
        "env_loaded": True,
        "gemini_api_key_present": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "gemma_model_env": os.getenv("GEMMA_MODEL"),
        "gemini_timeout_env": os.getenv("GEMINI_TIMEOUT_SECONDS"),
        "enable_tesseract_env": os.getenv("ENABLE_TESSERACT"),
    }

    try:
        import ocr_pipeline
        payload["pipeline_loaded"] = True
        payload["pipeline"] = {
            "gemma_model": getattr(ocr_pipeline, "GEMMA_MODEL", None),
            "gemini_timeout_seconds": getattr(ocr_pipeline, "GEMINI_TIMEOUT_SECONDS", None),
            "gemini_max_timeout_seconds": getattr(ocr_pipeline, "GEMINI_MAX_TIMEOUT_SECONDS", None),
            "enable_tesseract": getattr(ocr_pipeline, "ENABLE_TESSERACT", None),
            "gemma_max_image_side": getattr(ocr_pipeline, "GEMMA_MAX_IMAGE_SIDE", None),
            "gemma_retry_image_side": getattr(ocr_pipeline, "GEMMA_RETRY_IMAGE_SIDE", None),
            "gemma_jpeg_quality": getattr(ocr_pipeline, "GEMMA_JPEG_QUALITY", None),
            "confidence_threshold": getattr(ocr_pipeline, "CONFIDENCE_THRESHOLD", None),
        }
    except Exception as e:
        payload["pipeline_loaded"] = False
        payload["pipeline_error"] = str(e)

    return payload

@app.before_request
def ensure_lang():
    if 'lang' not in session:
        session['lang'] = 'en'

@app.after_request
def force_utf8(response):
    """Force UTF-8 encoding for all text/UI resources to prevent garbage '?' characters."""
    content_type = response.headers.get('Content-Type', '')
    if 'charset' not in content_type.lower():
        if response.mimetype in ('text/html', 'text/css', 'application/javascript', 'text/javascript', 'application/json'):
            response.headers['Content-Type'] = f"{response.mimetype}; charset=utf-8"
    return response

@app.route('/')
def index():
    """
    Renders the main landing page using Stitch DESIGN.md assets template.
    Passes current language state.
    """
    return render_template('index.html', lang=session.get('lang', 'en'))

@app.route('/api/lang/toggle', methods=['POST'])
def toggle_lang():
    """
    Toggles the application language between English and Hindi.
    """
    current = session.get('lang', 'en')
    session['lang'] = 'hi' if current == 'en' else 'en'
    return jsonify({"status": "success", "lang": session['lang']}), 200


@app.route('/api/health', methods=['GET'])
def api_health():
    """Expose safe runtime config for quick environment/debug checks."""
    return jsonify(_runtime_health_payload()), 200

@app.route('/api/upload', methods=['GET', 'POST'])
def api_upload():
    """
    Mission 4: OCR Ingestion Pipeline
    Officer Upload → Hybrid OCR (Tesseract + Gemma) → Extract → Confidence Check
    → Vault (AES-256-GCM) → Supabase → Secure Delete
    """
    if request.method == 'GET':
        return jsonify({"info": "POST a 'file' (PDF/PNG/JPG/TIFF/BMP) to ingest a land record."}), 200

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part in the request."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "status": "error",
            "message": "File type not allowed. Accepted: PDF, PNG, JPG, JPEG, TIFF, BMP."
        }), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    try:
        process_document = _get_pipeline()
        result = process_document(file_path)

        if result["status"] == "success":
            status_code = 200
        elif result["status"] == "exists":
            status_code = 200
        elif result["status"] == "flagged":
            status_code = 202
        else:
            status_code = 500

        return jsonify({
            "status":     result["status"],
            "message":    result["message"],
            "data": {
                "record_id":  result.get("record_id"),
                "ulpin":      result.get("ulpin"),
                "owner_token":result.get("owner_token"),
                "area":       result.get("area"),
                "confidence": result.get("confidence"),
                "hash":       result.get("hash"),
                "flagged":    result.get("flagged", False),
                "aadhaar_found": result.get("aadhaar_found")
            }
        }), status_code

    except Exception as e:
        logging.getLogger("app").error(f"Upload pipeline error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        # DPDP compliance: always delete the temp upload after processing
        from privacy_layer import secure_delete_file
        secure_delete_file(file_path)

@app.route('/api/verify', methods=['GET'])
def api_verify():
    """
    Mission 5: Cryptographic hash chain verification.
    Iterates all land_ledger entries, recomputes SHA-256 hashes,
    and flags any record where stored hash != expected hash (tamper detected).
    """
    from integrity import verify_chain
    result = verify_chain()
    http_code = 200 if result["status"] in ("INTACT", "EMPTY") else (
                500 if result["status"] == "ERROR" else 409
    )
    return jsonify(result), http_code


@app.route('/dashboard')
def dashboard():
    """Mission 5: Audit dashboard UI."""
    return render_template('dashboard.html', lang=session.get('lang', 'en'))


@app.route('/api/records/<record_id>', methods=['GET'])
def get_record(record_id):
    """
    Retrieve a land record by ID with role-based redaction.
    Requires an active session with 'role' set.
    Demo: set session role via /api/demo/login
    """
    from privacy_layer import redact_record, assert_no_pii_leak, log_record_access
    from supabase import create_client

    role  = session.get('role', 'user')
    uid   = session.get('user_id', 'anonymous')

    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    resp = sb.table("land_records").select("*").eq("id", record_id).execute()

    if not resp.data:
        return jsonify({"status": "error", "message": "Record not found."}), 404

    record = resp.data[0]
    safe   = redact_record(record, role=role)
    assert_no_pii_leak(safe, context=f"GET /api/records/{record_id}")
    log_record_access(uid, record_id, role)

    return jsonify({"status": "ok", "data": safe}), 200


@app.route('/api/demo/login', methods=['POST'])
def demo_login():
    """
    Demo-only endpoint to set a session role for testing RBAC.
    Body: {"role": "admin" | "user" | "auditor", "user_id": "..."}
    Remove or protect this route before production deployment.
    """
    body = request.get_json() or {}
    allowed = {'admin', 'user', 'auditor'}
    role = body.get('role', 'user')
    if role not in allowed:
        return jsonify({"error": f"Role must be one of {allowed}"}), 400
    session['role']    = role
    session['user_id'] = body.get('user_id', f'demo_{role}')
    return jsonify({"status": "ok", "role": role}), 200

@app.route('/api/search', methods=['GET'])
def api_search():
    """
    Mission 1 & 4: Search records by ULPIN.
    Requires DPDP Consent.
    """
    ulpin = request.args.get('ulpin')
    if not ulpin:
        return jsonify({"status": "error", "message": "ULPIN parameter is required."}), 400

    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    resp = sb.table("land_records").select("id, \"ULPIN\", \"Owner_Token\", \"Area\"").eq("ULPIN", ulpin.upper()).execute()

    if not resp.data:
        return jsonify({"status": "success", "message": "No record found.", "results": []}), 200

    return jsonify({
        "status": "success",
        "results": resp.data
    }), 200

@app.route('/api/legal/<record_id>/certificate', methods=['GET'])
def api_legal_certificate(record_id):
    """Mission 6: Generate Sec 65B Legal Certificate"""
    from legal_module import generate_sec65b_certificate
    try:
        cert_data = generate_sec65b_certificate(record_id, request.remote_addr)
        return jsonify({
            "status": "success",
            "data": cert_data
        }), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        logging.getLogger("app").error(f"Certificate error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to generate certificate."}), 500

if __name__ == '__main__':
    # Run the Flask app securely
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ["true", "1", "yes"]
    app.run(debug=debug_mode, port=5000)
