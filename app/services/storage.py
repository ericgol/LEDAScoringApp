"""Azure Blob Storage service wrapper.

Uses DefaultAzureCredential for auth (managed identity in Azure).
Falls back to local filesystem when Azure Storage is not configured.
"""

from __future__ import annotations
import logging
import os
import uuid
from typing import Optional

from flask import current_app

logger = logging.getLogger(__name__)


def _get_blob_service_client():
    """Create BlobServiceClient using DefaultAzureCredential."""
    account_name = current_app.config.get("AZURE_STORAGE_ACCOUNT_NAME")
    if not account_name:
        return None

    from azure.storage.blob import BlobServiceClient
    from azure.identity import DefaultAzureCredential

    account_url = current_app.config.get(
        "AZURE_STORAGE_BLOB_ENDPOINT",
        f"https://{account_name}.blob.core.windows.net",
    )
    return BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())


def upload_image(image_data: bytes, filename: str, session_id: str) -> dict:
    """Upload an image to Azure Blob Storage or local filesystem.

    Args:
        image_data: Raw image bytes.
        filename: Original filename.
        session_id: Scoring session ID for organizing uploads.

    Returns:
        Dict with storage location info.
    """
    # Generate a unique blob name to avoid collisions
    ext = os.path.splitext(filename)[1] or ".jpg"
    blob_name = f"{session_id}/{uuid.uuid4().hex}{ext}"

    client = _get_blob_service_client()

    if client is not None:
        try:
            container_name = current_app.config.get("AZURE_STORAGE_CONTAINER_NAME", "drone-images")
            container_client = client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            blob_client.upload_blob(image_data, overwrite=True)

            return {
                "storage": "azure",
                "container": container_name,
                "blob_name": blob_name,
                "url": blob_client.url,
                "original_filename": filename,
            }
        except Exception as e:
            logger.error("Azure blob upload failed: %s", e)
            # Fall through to local storage
            logger.info("Falling back to local storage")

    # Local filesystem fallback
    upload_dir = os.path.join(current_app.config["LOCAL_UPLOAD_DIR"], session_id)
    os.makedirs(upload_dir, exist_ok=True)
    local_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}{ext}")

    with open(local_path, "wb") as f:
        f.write(image_data)

    return {
        "storage": "local",
        "path": local_path,
        "original_filename": filename,
        "blob_name": blob_name,
    }


def get_image_data(storage_info: dict) -> Optional[bytes]:
    """Retrieve image data from storage.

    Args:
        storage_info: Dict returned by upload_image().

    Returns:
        Image bytes, or None if retrieval fails.
    """
    if storage_info.get("storage") == "azure":
        client = _get_blob_service_client()
        if client:
            try:
                container_name = storage_info.get("container", "drone-images")
                blob_client = client.get_container_client(container_name).get_blob_client(
                    storage_info["blob_name"]
                )
                return blob_client.download_blob().readall()
            except Exception as e:
                logger.error("Failed to download blob: %s", e)
                return None

    elif storage_info.get("storage") == "local":
        path = storage_info.get("path")
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()

    return None
