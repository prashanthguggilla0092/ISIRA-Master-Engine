import os
from pathlib import Path

import toml


BASE_DIR = Path(__file__).resolve().parents[2]
SECRETS_FILE = BASE_DIR / ".streamlit" / "secrets.toml"

_secrets = toml.load(SECRETS_FILE) if SECRETS_FILE.exists() else {}

GCP_PROJECT_ID = os.getenv(
    "GOOGLE_CLOUD_PROJECT",
    _secrets.get("GCP", {}).get("PROJECT_ID", "prashanth-genai-practice-2026"),
)

GCP_LOCATION = os.getenv(
    "GOOGLE_CLOUD_LOCATION",
    _secrets.get("GCP", {}).get("LOCATION", "us-central1"),
)

SPREADSHEET_ID = _secrets.get("GOOGLE_SHEETS", {}).get("SPREADSHEET_ID", "")
SERVICE_ACCOUNT_INFO = _secrets.get("GOOGLE_SHEETS", {}).get(
    "SERVICE_ACCOUNT_KEY",
    {},
)
