### smart_inbox_prototype/main.py
"""
Minimal event‑driven smart‑inbox prototype (Path B)
--------------------------------------------------
• Works with **Gmail** push‑notifications today
• Outlook Graph subscription can be bolted‑on by implementing OutlookProvider (stub below)
• One file, <300 loc, zero external state aside from env vars

Prerequisites
-------------
$ pip install fastapi uvicorn openai google-api-python-client google-auth google-auth-httplib2 python-dotenv

Set environment variables (e.g. in a `.env`):
OPENAI_API_KEY=<your‑OpenAI‑key>
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/gsa.json  # domain‑wide delegated SA
GMAIL_USER=<you@example.com>
LABEL_CRITICAL=AI/Critical   # will be created if missing
LABEL_DIGEST=AI/DigestQueue
"""

import base64
import json
import logging
import os
from functools import lru_cache
from typing import Optional
import pathlib
from datetime import datetime

import openai
from fastapi import FastAPI, HTTPException, Request
from googleapiclient.discovery import build
import googleapiclient.errors
import google.auth.exceptions
from starlette.responses import JSONResponse
from starlette.responses import Response
from typing import List
from shared_constants import STATE_FILE
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def decode_pubsub_push(req_json: dict) -> Optional[dict]:
    """Return the Gmail change record or None for the empty-verification ping."""
    msg = req_json.get("message")
    if not msg or "data" not in msg:          # verification ping or malformed
        return None
    payload = base64.b64decode(msg["data"])
    return json.loads(payload)

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

class Settings:
    root = pathlib.Path(__file__).parent
    openai_key: str = os.getenv("OPENAI_API_KEY")
    gmail_user: str = os.getenv("GMAIL_USER", "me")  # OAuth uses "me" for current user
    label_critical: str = os.getenv("LABEL_CRITICAL", "AI/Critical")
    label_digest: str = os.getenv("LABEL_DIGEST", "AI/DigestQueue")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    importance_threshold: float = float(os.getenv("IMPORTANCE_THRESHOLD", "0.5"))

settings = Settings()
openai.api_key = settings.openai_key

# ---------------------------------------------------------------------------
# Provider abstractions
# ---------------------------------------------------------------------------

class EmailProvider:
    """Abstract base class."""

    def fetch_message(self, message_id: str) -> dict:
        raise NotImplementedError

    def label_message(self, message_id: str, important: bool):
        raise NotImplementedError


class GmailProvider(EmailProvider):
    _service = None

    def _get_service(self):
        if self.__class__._service is None:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
            creds = None
            
            # Token file stores the user's access and refresh tokens
            token_file = settings.root / "token.json"
            
            if token_file.exists():
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        logging.error("Failed to refresh token: %s", e)
                        if not token_file.exists():
                            raise RuntimeError(
                                "No valid token.json found. Please run locally first to authenticate: "
                                "python scripts/create_oauth_token.py"
                            )
                        raise
                else:
                    # This will only work in development - fails in production
                    if not token_file.exists():
                        raise RuntimeError(
                            "No token.json found. In production, you must pre-generate token.json. "
                            "Run locally first: python scripts/create_oauth_token.py"
                        )
                    
                    # Only attempt interactive auth in development
                    import sys
                    if sys.stdin.isatty():  # Check if running interactively
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(settings.root / "oauth_client.json"), SCOPES
                        )
                        creds = flow.run_local_server(port=0)
                        # Save the credentials for the next run
                        token_file.write_text(creds.to_json())
                    else:
                        raise RuntimeError("Cannot perform interactive authentication in production")
            
            self.__class__._service = build("gmail", "v1", credentials=creds)
        return self.__class__._service

    @lru_cache(maxsize=2)
    def _get_label_id(self, name: str) -> str:
        service = self._get_service()
        labels = service.users().labels().list(userId="me").execute()["labels"]
        for lab in labels:
            if lab["name"] == name:
                return lab["id"]
        # create if missing
        body = {"name": name, "labelListVisibility": "labelShow"}
        lab = service.users().labels().create(userId="me", body=body).execute()
        return lab["id"]

    def fetch_message(self, message_id: str) -> dict:
        msg = (
            self._get_service()
            .users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return msg

    def label_message(self, message_id: str, important: bool):
        label_id = (
            self._get_label_id(settings.label_critical)
            if important
            else self._get_label_id(settings.label_digest)
        )
        body = {"addLabelIds": [label_id]}
        (
            self._get_service()
            .users()
            .messages()
            .modify(userId="me", id=message_id, body=body)
            .execute()
        )


class OutlookProvider(EmailProvider):
    """Stub – implement Graph API here when ready."""

    def fetch_message(self, message_id: str) -> dict:  # pragma: no cover
        raise NotImplementedError("Outlook Graph integration not yet implemented")

    def label_message(self, message_id: str, important: bool):  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Simple OpenAI classifier
# ---------------------------------------------------------------------------

def score_importance(subject: str, snippet: str) -> float:
    prompt = (
        "You are an email triage model. "
        "Output ONLY a number between 0 and 1 representing how critical this message is "
        "for immediate attention by a portfolio manager at a hedge fund. "
        "Key factors: trade failures, investor inquiries, compliance alerts. "
        "Ignore routine market research.\n\n"
        f"Subject: {subject}\nBody: {snippet[:800]}"
    )
    resp = openai.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4,
        temperature=0.0,
    )
    try:
        return float(resp.choices[0].message.content.strip())
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

app = FastAPI()
provider: EmailProvider = GmailProvider()

# Check for any previously missing messages on startup
missing_messages_file = pathlib.Path(__file__).parent / "missing_messages.log"
if missing_messages_file.exists():
    with open(missing_messages_file, "r") as f:
        missing_count = len(f.readlines())
    if missing_count > 0:
        logging.warning(
            "⚠️ Found %d previously missing messages in missing_messages.log - "
            "these may have been important emails that were deleted!",
            missing_count
        )

# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

# Initialize last_id later to avoid authentication errors at startup
last_id = None

def initialize_state():
    """Initialize state from file or Gmail profile. Called on first request."""
    global last_id
    if last_id is not None:
        return  # Already initialized
    
    try:
        last_id = json.loads(STATE_FILE.read_text())["last_id"]
        logging.info("Loaded last_id from state file: %s", last_id)
    except (FileNotFoundError, json.JSONDecodeError):
        # first boot or file wiped – start one below current mailbox id
        try:
            gmail = provider._get_service()
            profile = gmail.users().getProfile(userId="me").execute()
            last_id = int(profile["historyId"]) - 1
            logging.info("Initialized last_id from Gmail profile: %s", last_id)
        except Exception as e:
            logging.error("Failed to initialize from Gmail: %s", e)
            # Default to a safe value - Gmail will return 400 on first request
            # and we'll reset based on the incoming notification
            last_id = 1
            logging.warning("Using default last_id=1, will reset on first notification")

# ---------------------------------------------------------------------------
# Message Processing Helper
# ---------------------------------------------------------------------------

def process_message(msg_id: str, metadata: dict = None):
    """Process a single message: fetch, score, and label."""
    if metadata is None:
        metadata = {}
        
    try:
        raw = provider.fetch_message(msg_id)
        headers = {h["name"]: h["value"] for h in raw["payload"]["headers"]}
        subject = headers.get("Subject", "(no subj)")
        from_email = headers.get("From", "unknown")
        snippet = raw.get("snippet", "")
        
        logging.info("📧 Processing email: '%s' from %s", subject[:50], from_email)
        
        score = score_importance(subject, snippet)
        is_important = score >= settings.importance_threshold
        
        label_applied = settings.label_critical if is_important else settings.label_digest
        provider.label_message(msg_id, is_important)
        
        logging.info(
            "✅ Classified: Score=%.2f %s → Label: %s", 
            score, 
            "🔴 IMPORTANT" if is_important else "📋 Digest",
            label_applied
        )
    except googleapiclient.errors.HttpError as e:
        if e.resp.status == 404:
            # Message was deleted or is inaccessible - this could be critical!
            logging.error(
                "⚠️ MISSING MESSAGE: %s - Message in history but not fetchable. "
                "Thread: %s, Labels: %s. This could be a deleted important email!", 
                msg_id, metadata.get("threadId", "unknown"), metadata.get("labelIds", [])
            )
            # In production, you might want to:
            # - Send an alert to administrators
            # - Store the message ID for investigation
            # - Check if this happens frequently (potential attack?)
            
            # For now, let's save these to a file for review
            missing_messages_file = settings.root / "missing_messages.log"
            with open(missing_messages_file, "a") as f:
                f.write(f"{datetime.now().isoformat()}: Message {msg_id} "
                       f"(thread: {metadata.get('threadId', 'unknown')}, "
                       f"labels: {metadata.get('labelIds', [])}) was in history but returned 404\n")
        else:
            raise
    except Exception as exc:
        logging.exception("Failed to process message %s", msg_id)
        # We don't re-raise here to avoid stopping the whole batch

# ---------------------------------------------------------------------------
# Push Handler
# ---------------------------------------------------------------------------

@app.post("/gmail/push")
async def gmail_push(request: Request):
    global last_id
    
    # Initialize state on first request if needed
    initialize_state()
    
    try:
        blob = await request.json()
    except Exception:
        # Non-JSON (shouldn't happen with Pub/Sub) – swallow & ack
        return Response(status_code=204)

    data = decode_pubsub_push(blob)
    if data is None:
        # Verification ping
        return Response(status_code=204)

    hist_id = data["historyId"]
    email_address = data.get("emailAddress", "unknown")
    
    logging.info("Received push notification for %s with historyId %s", email_address, hist_id)
    
    # ❶ Fetch deltas since *last_id* (not since hist_id!)
    gmail = provider._get_service()
    try:
        # Only try to fetch history if we have a valid last_id
        if last_id and last_id > 1:
            logging.info("Checking for new messages since last_id=%s (current notification=%s)", last_id, hist_id)
            
            # Skip if this notification is older than what we've already processed
            if int(hist_id) <= last_id:
                logging.info("Skipping old notification (historyId %s <= last_id %s)", hist_id, last_id)
                return {"status": "skipped", "reason": "old_notification"}
            
            changes = gmail.users().history().list(
                userId="me",
                startHistoryId=str(last_id),
                historyTypes=["messageAdded"]
            ).execute()
            
            history_items = changes.get("history", [])
            logging.info("Found %d history items to process", len(history_items))
            
            # ❷ Process each added message
            message_count = 0
            for h in history_items:
                for m in h.get("messagesAdded", []):
                    message_count += 1
                    msg_id = m["message"]["id"]
                    # Extract any available metadata from history
                    thread_id = m["message"].get("threadId", "unknown")
                    label_ids = m["message"].get("labelIds", [])
                    
                    logging.info("Processing message %d: %s (thread: %s, labels: %s)", 
                               message_count, msg_id, thread_id, label_ids)
                    
                    # Pass metadata in case message fetch fails
                    process_message(msg_id, {"threadId": thread_id, "labelIds": label_ids})
                # Update checkpoint after processing each history item
                last_id = max(last_id, int(h["id"]))
            
            if message_count == 0:
                logging.info("No new messages in this notification")
            else:
                logging.info("Processed %d messages total", message_count)
        else:
            # If no valid last_id, just update to current and skip processing
            # This happens on first notification after setup
            logging.info("No valid last_id, updating to current historyId: %s", hist_id)
            last_id = int(hist_id)
            
    except googleapiclient.errors.HttpError as e:
        if e.resp.status == 400 or e.resp.status == 404:  
            # Stale or invalid ID – reset to current notification's ID
            logging.warning("History ID invalid/stale; resetting to %s", hist_id)
            last_id = int(hist_id)
            STATE_FILE.write_text(json.dumps({"last_id": last_id}))
            return Response(status_code=204)
        raise
    except google.auth.exceptions.RefreshError as e:
        logging.error("Authentication failed: %s", e)
        logging.error("Please ensure you have valid OAuth credentials in token.json")
        # Return 200 so Pub/Sub doesn't keep retrying
        return {"status": "auth_error", "message": str(e)}

    # ❸ Persist new checkpoint
    STATE_FILE.write_text(json.dumps({"last_id": last_id}))
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# Graceful Shutdown
# ---------------------------------------------------------------------------

@app.on_event("shutdown")
def save_checkpoint():
    if last_id is not None:
        STATE_FILE.write_text(json.dumps({"last_id": last_id}))

# Health‑check (for Cloud Run / ALB)
@app.get("/healthz")
async def health():
    return {"status": "up"}

# ---------------------------------------------------------------------------
# Local dev entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=False)
