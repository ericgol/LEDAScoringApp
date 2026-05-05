"""Image upload API routes."""

from flask import Blueprint, request, jsonify
from app.services import storage as storage_service

upload_bp = Blueprint("upload", __name__, url_prefix="/api")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "tiff", "tif", "bmp", "dng", "raw"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route("/upload", methods=["POST"])
def upload_images():
    """Upload one or more images for a scoring session.

    Expects multipart/form-data with:
      - session_id: scoring session ID
      - files[]: one or more image files
    """
    session_id = request.form.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    files = request.files.getlist("files[]")
    if not files:
        # Try alternate field name
        files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    results = []
    errors = []

    for f in files:
        if not f.filename:
            continue
        if not _allowed_file(f.filename):
            errors.append({"filename": f.filename, "error": "File type not allowed"})
            continue

        image_data = f.read()
        if len(image_data) == 0:
            errors.append({"filename": f.filename, "error": "Empty file"})
            continue

        storage_info = storage_service.upload_image(image_data, f.filename, session_id)
        results.append({
            "filename": f.filename,
            "storage_info": storage_info,
        })

    return jsonify({
        "uploaded": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    })
