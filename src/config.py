"""
Configuration for RAG agent and data ingestion.

Loads settings from .env file in project root.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def _require(var_name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")
    return value


# GCP Project Configuration
PROJECT_ID = _require("PROJECT_ID")
LOCATION = _require("LOCATION")
REGION = _require("REGION")

# Vertex AI Search Datastore
DATASTORE_ID = _require("DATASTORE_ID")

# Google Cloud Storage
BUCKET_NAME = _require("BUCKET_NAME")
SITE_PREFIX = _require("SITE_PREFIX")

# Model Configuration
MODEL = _require("MODEL")

# Credentials file path
CREDENTIALS_FILE = _require("GOOGLE_APPLICATION_CREDENTIALS")
