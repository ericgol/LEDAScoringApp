"""Scoring and analysis API routes."""

from flask import Blueprint, request, jsonify, render_template
from app.models.course import (
    get_course, get_session, update_session, ScoringSession, create_session,
)
from app.services import vision as vision_service
from app.services import storage as storage_service
from app.services import scoring as scoring_service

scoring_bp = Blueprint("scoring", __name__, url_prefix="/api")


@scoring_bp.route("/sessions", methods=["POST"])
def create_scoring_session():
    """Create a new scoring session.

    Expects JSON body with pilot info and course selection.
    """
    data = request.get_json(silent=True) or {}

    course_id = data.get("course_id")
    if not course_id:
        return jsonify({"error": "course_id is required"}), 400

    course = get_course(course_id)
    if not course:
        return jsonify({"error": f"Course '{course_id}' not found"}), 404

    session = ScoringSession(
        course_id=course_id,
        pilot_last_name=data.get("pilot_last_name", ""),
        pilot_first_name=data.get("pilot_first_name", ""),
        pilot_organization=data.get("pilot_organization", ""),
        drone_make=data.get("drone_make", ""),
        drone_model=data.get("drone_model", ""),
        facility_location=data.get("facility_location", ""),
        proctor_name=data.get("proctor_name", ""),
        date=data.get("date", ""),
        lane_spacing=data.get("lane_spacing", "5 FT"),
        lighting=data.get("lighting", "Daylight"),
        wind_average_mph=data.get("wind_average_mph", ""),
        wind_gusts_mph=data.get("wind_gusts_mph", ""),
        pilot_view=data.get("pilot_view", "Line of Sight"),
        status="in_progress",
    )
    create_session(session)

    return jsonify({
        "session_id": session.id,
        "course": course.name,
        "total_images_expected": course.total_images,
        "maneuvers": [
            {"id": m.id, "name": m.name, "short_name": m.short_name, "image_count": m.image_count}
            for m in course.maneuvers
        ],
    }), 201


@scoring_bp.route("/sessions/<session_id>", methods=["GET"])
def get_scoring_session(session_id):
    """Get session details and current results."""
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    course = get_course(session.course_id)
    return jsonify({
        "session": session.to_dict(),
        "course": course.to_dict() if course else None,
    })


@scoring_bp.route("/analyze", methods=["POST"])
def analyze_images():
    """Upload images, analyze with Computer Vision, and score them.

    Accepts multipart/form-data with:
      - session_id: scoring session ID
      - files[]: image files in maneuver order
    """
    session_id = request.form.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    course = get_course(session.course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    files = request.files.getlist("files[]") or request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    # Build flat list of expected buckets across all maneuvers
    expected_sequence = []
    for maneuver in course.maneuvers:
        for step in maneuver.steps:
            if step.captures_image:
                expected_sequence.append({
                    "maneuver_id": maneuver.id,
                    "maneuver_name": maneuver.name,
                    "step_number": step.step_number,
                    "expected_bucket": step.expected_bucket,
                    "instruction": step.instruction,
                })

    # Track bucket IDs seen in sequence for duplicate / out-of-order detection.
    # Each entry is the OCR-detected bucket ID string (or None if unreadable).
    seen_bucket_ids: list[str] = []

    results = []
    for i, f in enumerate(files):
        if not f.filename:
            continue

        image_data = f.read()
        if len(image_data) == 0:
            continue

        # Store the image
        storage_info = storage_service.upload_image(image_data, f.filename, session_id)

        # Analyze with Computer Vision
        analysis = vision_service.analyze_image(image_data, f.filename)

        # Match to expected sequence
        expected = expected_sequence[i] if i < len(expected_sequence) else {
            "maneuver_id": "extra",
            "maneuver_name": "Extra",
            "step_number": i + 1,
            "expected_bucket": "?",
            "instruction": "Extra image beyond expected sequence",
        }

        # Score the image
        score = scoring_service.score_image(analysis, expected["expected_bucket"])

        # ------------------------------------------------------------------ #
        # Duplicate / out-of-order detection                                  #
        #   - Consecutive retake of the same bucket  → allowed (is_duplicate) #
        #   - Retake of a bucket seen earlier but not just before → FAIL      #
        # ------------------------------------------------------------------ #
        bucket_id_ocr = analysis.get("bucket_id_ocr")
        is_duplicate = False
        is_out_of_order = False

        if bucket_id_ocr:
            if seen_bucket_ids and seen_bucket_ids[-1] == bucket_id_ocr:
                # Consecutive retake of the same bucket — allowed
                is_duplicate = True
            elif bucket_id_ocr in seen_bucket_ids:
                # Revisiting a bucket that appeared earlier in the sequence — not allowed
                is_out_of_order = True
                score["result"] = "fail"
                score["reason"] = (
                    f"Out-of-order retake: bucket {bucket_id_ocr} was already "
                    f"photographed earlier in the sequence"
                )
            seen_bucket_ids.append(bucket_id_ocr)

        score["is_duplicate"] = is_duplicate
        score["is_out_of_order"] = is_out_of_order

        result = {
            "image_index": i,
            "filename": f.filename,
            "maneuver_id": expected["maneuver_id"],
            "maneuver_name": expected["maneuver_name"],
            "step_number": expected["step_number"],
            "expected_bucket": expected["expected_bucket"],
            "instruction": expected["instruction"],
            "storage_info": storage_info,
            "analysis": analysis,
            "score": score,
        }
        results.append(result)

    # Update session with results
    session.image_results = results
    session.status = "completed"
    update_session(session)

    # Compute aggregate score
    scores = [r["score"] for r in results]
    summary = scoring_service.score_session(scores)

    return jsonify({
        "session_id": session_id,
        "images_processed": len(results),
        "images_expected": len(expected_sequence),
        "results": results,
        "summary": summary,
    })


@scoring_bp.route("/results/<session_id>", methods=["GET"])
def view_results(session_id):
    """Render the scoring results page for a session."""
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    course = get_course(session.course_id)
    scores = [r.get("score", {}) for r in session.image_results]
    summary = scoring_service.score_session(scores)

    return render_template(
        "results.html",
        session=session,
        course=course,
        summary=summary,
    )
