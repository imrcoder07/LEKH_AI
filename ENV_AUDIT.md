# Environment Audit

## Current Size

- Project total: about `610 MB`
- Virtual environment: about `610 MB`

## Directly Needed By This App

These are used by the current project code or declared in `requirements.txt`:

- `Flask`
- `flask-cors`
- `python-dotenv`
- `supabase`
- `cryptography`
- `pytesseract`
- `opencv-python-headless`
- `numpy`
- `Pillow`
- `google-generativeai`

## Large Packages That Appear Legitimate

- `cv2`
  - Provided by `opencv-python-headless`
  - Used in `ocr_pipeline.py`
- `numpy` and `numpy.libs`
  - Used in `ocr_pipeline.py`
- `google-api-python-client`
  - Brought in by `google-generativeai`
- `google`, `grpc`
  - Transitive dependencies of Gemini client

## Large Packages That Look Like Leftovers

These do not appear to be imported by the project files:

- `PyMuPDF`
  - Installed because of `pdf2docx`
- `pdf2docx`
  - Not used by app code
- `imgaug`
  - Not used by app code
  - `pip check` reports it is already missing dependencies
- `networkx`
  - Not used by app code
- `opencv-python`
  - Redundant alongside `opencv-python-headless`
  - Installed because of `imgaug`
- `opencv-contrib-python`
  - Not used by app code
- `visualdl` / broken `~isualdl`
  - Not used by app code
  - Environment reports an invalid distribution
- `hf-xet`
  - Not used by app code
- `hive_metastore`
  - Not used by app code
- `Cython`
  - Not used by app code at runtime

## Notes

- `pypdfium2` is declared in `requirements.txt` but is not currently installed.
- Upload is not fully working yet.
  - The endpoint responds.
  - The current result is `flagged`, not successful storage.
  - Main blockers remain missing Tesseract and failing Gemini access in this environment.

## Safest Cleanup Strategy

The safest option is to rebuild the virtual environment from `requirements.txt` instead of uninstalling packages one by one from the current `venv`.

Why:

- The current `venv` has accumulated unrelated packages.
- Some packages are partially broken already.
- Rebuilding avoids guessing which transitive dependencies matter.

## Likely Removable From Current Venv

If you decide to clean the current environment manually, these are the strongest removal candidates:

- `pdf2docx`
- `PyMuPDF`
- `imgaug`
- `networkx`
- `opencv-python`
- `opencv-contrib-python`
- `hf-xet`
- `Cython`

Use caution with:

- `google-api-python-client`
  - Large, but currently required by `google-generativeai`
- `visualdl`
  - Broken install artifact; cleanup may need manual file removal if pip cannot handle it

