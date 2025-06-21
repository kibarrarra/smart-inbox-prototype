### smart_inbox_prototype/main.py
"""
Stateless event-driven smart-inbox prototype
-------------------------------------------
• Gmail push-notifications today
• Outlook stub ready for Graph later
• No token.json on disk – creds built on the fly
Prereqs:
    pip install fastapi uvicorn openai google-api-python-client \
                google-auth google-auth-httplib2 python-dotenv
"""

from __future__ import annotations
import base64, json, logging, os, pathlib
from datetime import datetime
from functools import lru_cache
from typing import Optional, List

import openai
from fastapi import FastAPI, HTTPException, Request
from starlette.responses import Response, JSONResponse
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
import googleapiclient.errors
import google.auth.exceptions

from src.config import cfg            # unified secrets loader
from src.constants import STATE_FILE

# ──────────────────────────────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────────────────────────────
class Settings:
    label_critical: str = os.getenv("LABEL_CRITICAL", "AI/Critical")
    label_urgent:   str = os.getenv("LABEL_URGENT",   "AI/Urgent")
    label_medium:   str = os.getenv("LABEL_MEDIUM",   "AI/Medium")
    label_digest:   str = os.getenv("LABEL_DIGEST",   "AI/DigestQueue")
    openai_model:   str = os.getenv("OPENAI_MODEL",   "gpt-4o-mini")
    importance_threshold: float = float(os.getenv("IMPORTANCE_THRESHOLD", 0.5))
    urgent_threshold: float = float(os.getenv("URGENT_THRESHOLD", 0.8))
    medium_threshold: float = float(os.getenv("MEDIUM_THRESHOLD", 0.4))

settings = Settings()
openai.api_key = cfg.OPENAI_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# ──────────────────────────────────────────────────────────────────────
# Gmail client helper (stateless)
# ──────────────────────────────────────────────────────────────────────
def gmail_client():
    """Return a Gmail API client with a fresh access token (no token.json)."""
    creds = Credentials(
        None,
        refresh_token=cfg.refresh_token,
        client_id=cfg.client_id,
        client_secret=cfg.client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
    if not creds.valid or creds.expired:
        creds.refresh(GoogleAuthRequest())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

# ──────────────────────────────────────────────────────────────────────
# Provider abstraction
# ──────────────────────────────────────────────────────────────────────
class EmailProvider:
    def fetch_message(self, msg_id: str) -> dict: ...
    def label_message(self, msg_id: str, score: float): ...

class GmailProvider(EmailProvider):
    _svc = None

    def _service(self):
        if self.__class__._svc is None:
            self.__class__._svc = gmail_client()
        return self.__class__._svc

    @lru_cache(maxsize=2)
    def _label_id(self, name: str) -> str:
        svc = self._service()
        for lab in svc.users().labels().list(userId="me").execute()["labels"]:
            if lab["name"] == name:
                return lab["id"]
        # create if missing
        body = {"name": name, "labelListVisibility": "labelShow"}
        return svc.users().labels().create(userId="me", body=body).execute()["id"]

    def fetch_message(self, msg_id: str) -> dict:
        return self._service().users().messages().get(
            userId="me", id=msg_id, format="full"
        ).execute()

    def label_message(self, msg_id: str, score: float):
        """Apply intelligent labels based on importance score"""
        if score >= settings.urgent_threshold:
            label = self._label_id(settings.label_critical)
        elif score >= settings.importance_threshold:
            label = self._label_id(settings.label_urgent)
        elif score >= settings.medium_threshold:
            label = self._label_id(settings.label_medium)
        else:
            label = self._label_id(settings.label_digest)
            
        self._service().users().messages().modify(
            userId="me", id=msg_id, body={"addLabelIds": [label]}
        ).execute()

class OutlookProvider(EmailProvider):
    """Stub – implement Graph API later."""
    def fetch_message(self, msg_id: str) -> dict: raise NotImplementedError
    def label_message(self, msg_id: str, score: float): raise NotImplementedError

provider: EmailProvider = GmailProvider()

# ──────────────────────────────────────────────────────────────────────
# Utility funcs
# ──────────────────────────────────────────────────────────────────────
def decode_pubsub_push(blob: dict) -> Optional[dict]:
    msg = blob.get("message", {})
    data = msg.get("data")
    return json.loads(base64.b64decode(data)) if data else None

def score_importance(subject: str, snippet: str) -> float:
    prompt = (
        "You are an intelligent email triage system for a finance professional. "
        "Score emails 0.0-1.0 based on urgency and business impact.\n\n"
        "HIGH PRIORITY (0.7-1.0):\n"
        "- Trade execution issues, margin calls, system outages\n"
        "- Client escalations, regulatory deadlines, risk alerts\n"
        "- Meeting invites from executives or key clients\n"
        "- Time-sensitive market opportunities\n\n"
        "MEDIUM PRIORITY (0.3-0.6):\n"
        "- Regular business communications, meeting requests\n"
        "- Non-urgent reports, internal updates\n"
        "- Vendor communications, routine notifications\n\n"
        "LOW PRIORITY (0.0-0.2):\n"
        "- Newsletters, marketing emails, social media\n"
        "- Automated reports, non-critical updates\n"
        "- Personal emails unrelated to work\n\n"
        "Respond with ONLY the numeric score (e.g., 0.8).\n\n"
        f"Subject: {subject}\n"
        f"Body: {snippet[:800]}"
    )
    resp = openai.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=8,
        temperature=0.1,
    )
    try:   
        score = float(resp.choices[0].message.content.strip())
        return max(0.0, min(1.0, score))  # Clamp to 0-1 range
    except ValueError: 
        return 0.0

# ──────────────────────────────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────────────────────────────
app = FastAPI()
last_id: Optional[int] = None

def init_last_id():
    global last_id
    if last_id is not None: return
    try:
        last_id = int(json.loads(STATE_FILE.read_text())["last_id"])
    except Exception:
        prof = gmail_client().users().getProfile(userId="me").execute()
        last_id = int(prof["historyId"]) - 1

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.post("/gmail/push")
async def gmail_push(req: Request):
    global last_id
    init_last_id()

    try:
        blob = await req.json()
    except Exception as e:
        logging.error(f"Failed to parse request body: {e}")
        body = await req.body()
        logging.error(f"Raw body: {body}")
        return Response(status_code=400)
        
    logging.info(f"Received push notification: {json.dumps(blob, indent=2)}")
    
    data = decode_pubsub_push(blob)
    if data is None:
        logging.warning("Could not decode push notification data")
        return Response(status_code=204)

    hist_id = int(data["historyId"])
    if hist_id <= last_id:
        return JSONResponse({"status": "skipped-old"})

    svc = gmail_client()
    try:
        if last_id > 1:
            changes = svc.users().history().list(
                userId="me",
                startHistoryId=str(last_id),
                historyTypes=["messageAdded"]
            ).execute().get("history", [])
            for h in changes:
                for m in h.get("messagesAdded", []):
                    process_message(m["message"]["id"], m["message"])
                last_id = max(last_id, int(h["id"]))
        else:
            last_id = hist_id
    except googleapiclient.errors.HttpError as e:
        if e.resp.status in (400, 404):
            last_id = hist_id
        else:
            raise

    STATE_FILE.write_text(json.dumps({"last_id": last_id}))
    return JSONResponse({"status": "ok"})

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def process_message(msg_id: str, meta: dict):
    try:
        raw = provider.fetch_message(msg_id)
        headers = {h["name"]: h["value"] for h in raw["payload"]["headers"]}
        subj = headers.get("Subject", "(no subject)")
        score = score_importance(subj, raw.get("snippet", ""))
        provider.label_message(msg_id, score)
        logging.info("Scored %.2f on '%s'", score, subj[:60])
    except googleapiclient.errors.HttpError as e:
        logging.error("Error fetching %s: %s", msg_id, e)

# ──────────────────────────────────────────────────────────────────────
@app.get("/healthz")
async def health(): return {"status": "up"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0",
                port=int(os.getenv("PORT", 8080)), reload=False)
