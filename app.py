"""MedTech Knee Analysis Platform — Flask application."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from lib.case_store import get_analytics, save_case
from lib.image_processor import load_knee_image
from lib.implant_sizer import analyze_implant_sizing, result_to_dict as implant_to_dict
from lib.json_utils import json_safe
from lib.meniscus_analyzer import analyze_meniscus, result_to_dict as meniscus_to_dict
from lib.visualizer import create_visualization

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".dcm"}
MAX_FILE_SIZE = 50 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"Unsupported format. Use: {', '.join(sorted(ALLOWED_EXT))}"}), 400

    sex = request.form.get("sex", "male")
    age = request.form.get("age", "")
    oa_status = request.form.get("oa_status", "unknown")
    patient_id = request.form.get("patient_id", "")
    pixel_to_mm = request.form.get("pixel_to_mm", "").strip()
    px_val = None
    if pixel_to_mm:
        try:
            px_val = float(pixel_to_mm)
        except ValueError:
            return jsonify({"error": "Invalid pixel-to-mm value"}), 400

    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True)

    filename = secure_filename(file.filename) or f"scan{ext}"
    image_path = session_dir / filename
    file.save(image_path)

    try:
        img = load_knee_image(image_path)
        meniscus = analyze_meniscus(img, BASE_DIR, sex=sex, oa_status=oa_status, pixel_to_mm=px_val)
        implant = analyze_implant_sizing(img, BASE_DIR, pixel_to_mm=meniscus.pixel_to_mm)

        meniscus_dict = meniscus_to_dict(meniscus)
        implant_dict = implant_to_dict(implant)
        overlay_b64 = create_visualization(img, meniscus_dict, implant_dict)

        case_record = {
            "session_id": session_id,
            "patient_id": patient_id,
            "sex": sex,
            "age": age,
            "oa_status": oa_status,
            "mean_thickness_mm": meniscus.mean_thickness_mm,
            "oa_likelihood": meniscus.oa_assessment.get("ai_oa_likelihood"),
            "recommended_femoral_size": implant.recommended_femoral.size,
            "recommended_tibial_size": implant.recommended_tibial.size,
        }
        case_id = save_case(BASE_DIR, case_record)

        return jsonify(json_safe({
            "session_id": session_id,
            "case_id": case_id,
            "patient": {"id": patient_id, "sex": sex, "age": age, "oa_status": oa_status},
            "meniscus_analysis": meniscus_dict,
            "implant_sizing": implant_dict,
            "visualization": overlay_b64,
        }))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Analysis failed: {exc}"}), 500


@app.route("/api/analytics")
def analytics():
    return jsonify(json_safe(get_analytics(BASE_DIR)))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
