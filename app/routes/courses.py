"""Course management API routes."""

from flask import Blueprint, jsonify
from app.models.course import get_all_courses, get_course

courses_bp = Blueprint("courses", __name__, url_prefix="/api")


@courses_bp.route("/courses", methods=["GET"])
def list_courses():
    """List all available LEDA course levels."""
    courses = get_all_courses()
    return jsonify({
        "courses": [
            {
                "id": c.id,
                "name": c.name,
                "level": c.level,
                "description": c.description,
                "time_limit_minutes": c.time_limit_minutes,
                "total_images": c.total_images,
                "lane_spacing_options": c.lane_spacing_options,
                "maneuvers": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "short_name": m.short_name,
                        "image_count": m.image_count,
                        "expected_buckets": m.expected_buckets,
                    }
                    for m in c.maneuvers
                ],
            }
            for c in courses
        ]
    })


@courses_bp.route("/courses/<course_id>", methods=["GET"])
def get_course_detail(course_id):
    """Get detailed course definition including all maneuver steps."""
    course = get_course(course_id)
    if not course:
        return jsonify({"error": f"Course '{course_id}' not found"}), 404

    return jsonify(course.to_dict())
