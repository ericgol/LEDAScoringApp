"""Scoring engine for LEDA drone proficiency check-rides.

Currently provides placeholder scoring based on basic CV analysis.
Will be enhanced with custom vision model results once training data
and specific ring detection criteria are provided.

Scoring rule from LEDA:
  - UNBROKEN ring visible → PASS (circle bucket number)
  - BROKEN ring visible   → FAIL (X out bucket number)
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def score_image(analysis: dict, expected_bucket: str) -> dict:
    """Score a single image against its expected bucket.

    Args:
        analysis: CV analysis result dict from vision.py
        expected_bucket: Expected bucket ID (e.g., "1", "2A", "3B")

    Returns:
        Scoring result dict with pass/fail and confidence.
    """
    if analysis.get("status") in ("skipped", "error"):
        return {
            "expected_bucket": expected_bucket,
            "result": "pending",
            "confidence": 0.0,
            "reason": "Image analysis not available",
            "ring_detected": False,
            "ring_intact": None,
        }

    # --- Placeholder scoring logic ---
    # This will be replaced with a custom vision model that specifically
    # detects colored rings and determines if they are broken or intact.
    #
    # For now, we return the raw analysis and mark as "needs_review"
    # so a human proctor can verify.

    tags = analysis.get("tags", [])
    caption = analysis.get("caption", "")
    objects = analysis.get("objects", [])
    read_text = analysis.get("read_text", [])

    # Basic heuristics (will be replaced by custom model):
    # 1. Check if image contains circular/ring-like objects
    ring_keywords = {"circle", "ring", "round", "circular", "hoop", "band", "disk"}
    color_keywords = {"red", "blue", "green", "yellow", "orange", "purple", "white", "black"}

    detected_tags = {t["name"].lower() for t in tags}
    ring_detected = bool(ring_keywords & detected_tags)
    colors_detected = list(color_keywords & detected_tags)

    # 2. Check for any OCR text that might match bucket labels
    bucket_text_match = any(expected_bucket.lower() in t.lower() for t in read_text)

    return {
        "expected_bucket": expected_bucket,
        "result": "needs_review",  # Will be "pass" or "fail" with custom model
        "confidence": 0.0,
        "reason": "Automated scoring pending custom model training",
        "ring_detected": ring_detected,
        "ring_intact": None,  # None = unknown, True = unbroken, False = broken
        "colors_detected": colors_detected,
        "bucket_text_match": bucket_text_match,
        "caption": caption,
        "tag_count": len(tags),
        "object_count": len(objects),
    }


def score_session(image_results: list[dict]) -> dict:
    """Compute aggregate scoring for a complete session.

    Args:
        image_results: List of per-image scoring results.

    Returns:
        Aggregate scoring summary.
    """
    total = len(image_results)
    passed = sum(1 for r in image_results if r.get("result") == "pass")
    failed = sum(1 for r in image_results if r.get("result") == "fail")
    needs_review = sum(1 for r in image_results if r.get("result") == "needs_review")
    pending = sum(1 for r in image_results if r.get("result") == "pending")

    return {
        "total_images": total,
        "passed": passed,
        "failed": failed,
        "needs_review": needs_review,
        "pending": pending,
        "pass_rate": (passed / total * 100) if total > 0 else 0,
        "overall_result": "pass" if failed == 0 and needs_review == 0 and pending == 0 else "incomplete",
    }
