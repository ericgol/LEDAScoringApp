"""Azure Computer Vision service wrapper.

Uses azure-ai-vision-imageanalysis SDK with DefaultAzureCredential
(managed identity in Azure, az CLI locally).
Falls back to key-based auth if AZURE_COMPUTER_VISION_KEY is set.
"""

from __future__ import annotations
import logging
from typing import Optional

from flask import current_app

logger = logging.getLogger(__name__)


def _get_client():
    """Create and return an ImageAnalysisClient."""
    endpoint = current_app.config.get("AZURE_COMPUTER_VISION_ENDPOINT")
    if not endpoint:
        return None

    from azure.ai.vision.imageanalysis import ImageAnalysisClient
    key = current_app.config.get("AZURE_COMPUTER_VISION_KEY")

    if key:
        from azure.core.credentials import AzureKeyCredential
        return ImageAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    else:
        from azure.identity import DefaultAzureCredential
        return ImageAnalysisClient(endpoint=endpoint, credential=DefaultAzureCredential())


def analyze_image(image_data: bytes, image_name: str = "") -> dict:
    """Analyze a single image using Azure Computer Vision.

    Args:
        image_data: Raw image bytes.
        image_name: Optional filename for logging.

    Returns:
        Dict with analysis results including tags, objects, caption, and read (OCR).
        Returns a placeholder dict if Azure CV is not configured.
    """
    client = _get_client()
    if client is None:
        logger.warning("Azure Computer Vision not configured; returning placeholder analysis")
        return {
            "status": "skipped",
            "message": "Azure Computer Vision not configured",
            "image_name": image_name,
            "tags": [],
            "objects": [],
            "caption": "",
            "dense_captions": [],
            "read_text": [],
        }

    try:
        from azure.ai.vision.imageanalysis.models import VisualFeatures

        result = client.analyze(
            image_data=image_data,
            visual_features=[
                VisualFeatures.TAGS,
                VisualFeatures.OBJECTS,
                VisualFeatures.CAPTION,
                VisualFeatures.DENSE_CAPTIONS,
                VisualFeatures.READ,
            ],
        )

        # Extract structured results
        tags = []
        if result.tags:
            tags = [{"name": t.name, "confidence": t.confidence} for t in result.tags.values]

        objects = []
        if result.objects:
            for obj in result.objects.values:
                objects.append({
                    "name": obj.tags[0].name if obj.tags else "unknown",
                    "confidence": obj.tags[0].confidence if obj.tags else 0,
                    "bounding_box": {
                        "x": obj.bounding_box.x,
                        "y": obj.bounding_box.y,
                        "width": obj.bounding_box.width,
                        "height": obj.bounding_box.height,
                    },
                })

        caption = ""
        if result.caption:
            caption = result.caption.text

        dense_captions = []
        if result.dense_captions:
            dense_captions = [
                {"text": dc.text, "confidence": dc.confidence}
                for dc in result.dense_captions.values
            ]

        read_text = []
        if result.read:
            for block in result.read.blocks:
                for line in block.lines:
                    read_text.append(line.text)

        return {
            "status": "success",
            "image_name": image_name,
            "tags": tags,
            "objects": objects,
            "caption": caption,
            "dense_captions": dense_captions,
            "read_text": read_text,
        }

    except Exception as e:
        logger.error("Computer Vision analysis failed for %s: %s", image_name, e)
        return {
            "status": "error",
            "image_name": image_name,
            "error": str(e),
            "tags": [],
            "objects": [],
            "caption": "",
            "dense_captions": [],
            "read_text": [],
        }


def analyze_image_from_url(image_url: str) -> dict:
    """Analyze an image from a URL using Azure Computer Vision.

    Args:
        image_url: Publicly accessible URL to the image.

    Returns:
        Dict with analysis results.
    """
    client = _get_client()
    if client is None:
        return {
            "status": "skipped",
            "message": "Azure Computer Vision not configured",
            "image_url": image_url,
        }

    try:
        from azure.ai.vision.imageanalysis.models import VisualFeatures

        result = client.analyze_from_url(
            image_url=image_url,
            visual_features=[
                VisualFeatures.TAGS,
                VisualFeatures.OBJECTS,
                VisualFeatures.CAPTION,
                VisualFeatures.DENSE_CAPTIONS,
                VisualFeatures.READ,
            ],
        )

        tags = [{"name": t.name, "confidence": t.confidence}
                for t in (result.tags.values if result.tags else [])]
        objects = []
        if result.objects:
            for obj in result.objects.values:
                objects.append({
                    "name": obj.tags[0].name if obj.tags else "unknown",
                    "confidence": obj.tags[0].confidence if obj.tags else 0,
                })
        caption = result.caption.text if result.caption else ""

        return {
            "status": "success",
            "image_url": image_url,
            "tags": tags,
            "objects": objects,
            "caption": caption,
        }

    except Exception as e:
        logger.error("CV analysis failed for URL %s: %s", image_url, e)
        return {"status": "error", "image_url": image_url, "error": str(e)}
