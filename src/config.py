# config.py
"""Unified config loader.

Priority:
1. Explicit OS env vars            (export GMAIL_REFRESH_B64=…)
2. .env file in project root       (for local dev)
3. Google Secret Manager (prod)    (pull once at startup)

Drop-in:  `from config import cfg`
"""

import base64, json, os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from google.cloud import secretmanager  # safe to pip-install; ignored locally if GOOGLE_CLOUD_PROJECT unset

# ───────────────────────
# 1) .env for local dev
# ───────────────────────
load_dotenv()  # silently ignored if file absent

# ───────────────────────
# 2) helper
# ───────────────────────
def _maybe_secret(project: str, name: str, key: str = "latest") -> str | None:
    """If var missing & running in GCP, fetch Secret Manager payload once."""
    if not project:
        return None
    client = secretmanager.SecretManagerServiceClient()
    secret_path = f"projects/{project}/secrets/{name}/versions/{key}"
    try:
        payload = client.access_secret_version(name=secret_path).payload.data
        return payload.decode()
    except Exception:
        return None

# ---- Resolve every variable once at import time ----
_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")  # only set in Cloud Run / GKE

def _get(name: str, *, secret: str | None = None, required: bool = True) -> str | None:
    val = os.getenv(name)
    if val:
        return val
    if secret:
        val = _maybe_secret(_PROJECT, secret)
        if val:
            return val
    if required:
        raise RuntimeError(f"Missing config: {name} (set env var or use Secret Manager)")
    return None

class _Config:
    def __init__(self):
        # Allow graceful fallback for development
        try:
            # client creds (base64)
            self.CLIENT_ID_B64     = _get("GOOGLE_CLIENT_ID_B64",     secret="gmail-client-id")
            self.CLIENT_SECRET_B64 = _get("GOOGLE_CLIENT_SECRET_B64", secret="gmail-client-secret")
            self.REFRESH_B64       = _get("GMAIL_REFRESH_B64",        secret="gmail-refresh-token")
            self.OPENAI_KEY        = _get("OPENAI_API_KEY",           secret="openai-key")
            self.USER_EMAIL        = _get("GMAIL_USER", required=False)  # local only (no secret)
        except RuntimeError as e:
            print(f"⚠️  Config warning: {e}")
            print("💡 For local dev, set environment variables or run scripts/get_refresh_token.py")
            # Set None values so properties can handle gracefully
            self.CLIENT_ID_B64 = self.CLIENT_SECRET_B64 = self.REFRESH_B64 = self.OPENAI_KEY = self.USER_EMAIL = None

    # decoded helpers -------------------------------------------------
    @property
    def refresh_token(self) -> str:
        if not self.REFRESH_B64:
            raise RuntimeError("Gmail refresh token not configured")
        return json.loads(base64.b64decode(self.REFRESH_B64))["refresh_token"]

    @property
    def client_id(self) -> str:
        if not self.CLIENT_ID_B64:
            raise RuntimeError("Gmail client ID not configured")
        return base64.b64decode(self.CLIENT_ID_B64).decode()

    @property
    def client_secret(self) -> str:
        if not self.CLIENT_SECRET_B64:
            raise RuntimeError("Gmail client secret not configured")
        return base64.b64decode(self.CLIENT_SECRET_B64).decode()

cfg = _Config()
