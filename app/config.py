"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB max upload

    # Azure Storage
    AZURE_STORAGE_ACCOUNT_NAME = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "")
    AZURE_STORAGE_BLOB_ENDPOINT = os.environ.get("AZURE_STORAGE_BLOB_ENDPOINT", "")
    AZURE_STORAGE_CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "drone-images")

    # Azure Computer Vision
    AZURE_COMPUTER_VISION_ENDPOINT = os.environ.get("AZURE_COMPUTER_VISION_ENDPOINT", "")
    # Optional: key-based auth for local dev (managed identity preferred)
    AZURE_COMPUTER_VISION_KEY = os.environ.get("AZURE_COMPUTER_VISION_KEY", "")

    # Local storage fallback when Azure is not configured
    LOCAL_UPLOAD_DIR = os.environ.get("LOCAL_UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "uploads"))

    # Course data directory
    COURSE_DATA_DIR = os.environ.get("COURSE_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))

    @property
    def azure_configured(self) -> bool:
        """Check if Azure services are configured."""
        return bool(self.AZURE_STORAGE_ACCOUNT_NAME and self.AZURE_COMPUTER_VISION_ENDPOINT)
