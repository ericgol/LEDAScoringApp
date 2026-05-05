"""Scoring engine for LEDA drone proficiency check-rides.

Scoring rules from LEDA:
  - UNBROKEN ring visible AND bucket centered → PASS
  - BROKEN ring visible                       → FAIL
  - Bucket not in middle third of frame       → FAIL (positioning)
  - Out-of-order bucket retake                → FAIL
  - Consecutive retake of same bucket         → allowed (use best result)
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# Ring colors the LEDA standard uses on its targets
_RING_COLORS = {
    "red", "blue", "green", "yellow", "orange",
    "purple", "cyan", "white", "black", "pink",
}

# Tags from Azure CV that suggest a ring/circular target is present
_RING_KEYWORDS = {"circle", "ring", "round", "circular", "hoop", "band", "disk", "target"}


def check_centering(
    primary_object: dict | None,
    img_width: int | None,
    img_height: int | None,
) -> bool | None:
    """Return True if the primary object's centre falls in the middle third of
    both the horizontal and vertical axes (3x3 grid centre cell).

    Returns None when there is insufficient data to make a determination.
    """
    if not primary_object or not img_width or not img_height:
        return None
    bb = primary_object["bounding_box"]
    cx = bb["x"] + bb["width"] / 2
    cy = bb["y"] + bb["height"] / 2
    x_ok = (img_width / 3) <= cx <= (2 * img_width / 3)
    y_ok = (img_height / 3) <= cy <= (2 * img_height / 3)
    return x_ok and y_ok


def extract_ring_color(
    tags: list[dict],
    caption: str,
    dense_captions: list[dict],
) -> str | None:
    """Return the most likely ring color mentioned in Azure CV results.

    Checks tag names first (highest signal), then falls back to caption
    and dense-caption text.
    """
    for tag in tags:
        name = tag["name"].lower()
        if name in _RING_COLORS:
            return name
    all_text = " ".join(
        [caption] + [dc.get("text", "") for dc in dense_captions]
    ).lower()
    for color in _RING_COLORS:
        if color in all_text:
            return color
    return None


def score_image(analysis: dict, expected_bucket: str) -> dict:
    """Score a single image against its expected bucket.

    Args:
        analysis: CV analysis result dict from vision.py.
        expected_bucket: Expected bucket ID (e.g. "1A", "2D", "3B").

    Returns:
        Scoring result dict.  ``result`` will be one of:
        - ``"pass"``         — ring intact, bucket centred, ID matched
        - ``"fail"``         — definitive failure (positioning, out-of-order)
        - ``"needs_review"`` — CV ran but ring intact/broken undetermined
        - ``"pending"``      — CV unavailable
    """
    if analysis.get("status") in ("skipped", "error"):
        return {
            "expected_bucket": expected_bucket,
            "result": "pending",
            "confidence": 0.0,
            "reason": "Image analysis not available",
            "bucket_centered": None,
            "bucket_id_ocr": None,
            "bucket_id_match": None,
            "ring_detected": False,
            "ring_intact": None,
            "ring_color": None,
        }

    tags = analysis.get("tags", [])
    caption = analysis.get("caption", "")
    objects = analysis.get("objects", [])
    dense_captions = analysis.get("dense_captions", [])
    primary_object = analysis.get("primary_object")
    img_width = analysis.get("image_width")
    img_height = analysis.get("image_height")
    bucket_id_ocr = analysis.get("bucket_id_ocr")

    # ------------------------------------------------------------------ #
    # 1. Centering check — bucket must be in the centre third of the frame #
    # ------------------------------------------------------------------ #
    bucket_centered = check_centering(primary_object, img_width, img_height)

    # ------------------------------------------------------------------ #
    # 2. Bucket ID match via OCR                                          #
    # ------------------------------------------------------------------ #
    bucket_id_match: bool | None = None
    if bucket_id_ocr is not None:
        bucket_id_match = bucket_id_ocr.upper() == expected_bucket.upper()

    # ------------------------------------------------------------------ #
    # 3. Ring colour and presence                                         #
    # ------------------------------------------------------------------ #
    detected_tag_names = {t["name"].lower() for t in tags}
    ring_detected = bool(_RING_KEYWORDS & detected_tag_names)
    ring_color = extract_ring_color(tags, caption, dense_captions)

    # ------------------------------------------------------------------ #
    # 4. Determine result                                                 #
    # ------------------------------------------------------------------ #
    reasons: list[str] = []

    # Hard failure: bucket clearly not centred
    if bucket_centered is False:
        reasons.append("Bucket not in centre third of frame (positioning failure)")
        return {
            "expected_bucket": expected_bucket,
            "result": "fail",
            "confidence": 0.8,
            "reason": "; ".join(reasons),
            "bucket_centered": False,
            "bucket_id_ocr": bucket_id_ocr,
            "bucket_id_match": bucket_id_match,
            "ring_detected": ring_detected,
            "ring_intact": None,
            "ring_color": ring_color,
            "tag_count": len(tags),
            "object_count": len(objects),
            "caption": caption,
        }

    # Bucket is centred (or we can’t tell) — ring intact/broken still
    # requires a custom model; mark for human review.
    if bucket_centered is None:
        reasons.append("Could not determine bucket position (no objects detected)")
    if not ring_detected:
        reasons.append("No ring/target detected by CV — may be too distant")
    reasons.append("Ring intact vs. broken requires custom model — pending review")

    return {
        "expected_bucket": expected_bucket,
        "result": "needs_review",
        "confidence": 0.0,
        "reason": "; ".join(reasons),
        "bucket_centered": bucket_centered,
        "bucket_id_ocr": bucket_id_ocr,
        "bucket_id_match": bucket_id_match,
        "ring_detected": ring_detected,
        "ring_intact": None,   # True/False once custom model is trained
        "ring_color": ring_color,
        "tag_count": len(tags),
        "object_count": len(objects),
        "caption": caption,
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
    out_of_order = sum(1 for r in image_results if r.get("is_out_of_order"))
    duplicates = sum(1 for r in image_results if r.get("is_duplicate"))

    return {
        "total_images": total,
        "passed": passed,
        "failed": failed,
        "needs_review": needs_review,
        "pending": pending,
        "out_of_order_retakes": out_of_order,
        "consecutive_retakes": duplicates,
        "pass_rate": (passed / total * 100) if total > 0 else 0,
        "overall_result": "pass" if failed == 0 and needs_review == 0 and pending == 0 else "incomplete",
    }
