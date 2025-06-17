#!/usr/bin/env python
"""
create_watch.py -- create a Gmail Pub/Sub watch and push subscription
"""
from __future__ import annotations
import argparse, pathlib, os, json

import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.cloud import pubsub_v1
from google.api_core.exceptions import AlreadyExists, NotFound

# When installed with pip install -e ., these imports will work
from src.constants import STATE_FILE

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def ensure_label(gmail, label_name: str) -> str:
    # Return the label ID, creating it if needed
    labels_resp = gmail.users().labels().list(userId="me").execute()
    for lbl in labels_resp["labels"]:
        if lbl["name"] == label_name:
            return lbl["id"]

    new_lbl = gmail.users().labels().create(
        userId="me",
        body={"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    ).execute()
    print(f"✓ created Gmail label {label_name}")
    return new_lbl["id"]

# ─────────────────── argument parsing ────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--project",   required=True, help="GCP project ID")
parser.add_argument("--topic",     required=True, help="Pub/Sub topic name")
parser.add_argument("--push-endpoint", required=True,
                    help="Public HTTPS URL that Pub/Sub will POST to")
parser.add_argument("--subscription", default="gmail-watch-sub",
                    help="(optional) subscription name")
args = parser.parse_args()

# ──────────────────── OAuth (use config.py) ───────────────
from src.config import cfg
from google.auth.transport.requests import Request as GoogleAuthRequest

# Build credentials from refresh token (same as main.py)
creds = Credentials(
    None,
    refresh_token=cfg.refresh_token,
    client_id=cfg.client_id,
    client_secret=cfg.client_secret,
    token_uri="https://oauth2.googleapis.com/token",
    scopes=SCOPES,
)
if not creds.valid or creds.expired:
    creds.refresh(GoogleAuthRequest())

gmail = build("gmail", "v1", credentials=creds)

# ────────────── Pub/Sub topic + push subscription ────────
topic_full = f"projects/{args.project}/topics/{args.topic}"
sub_full   = f"projects/{args.project}/subscriptions/{args.subscription}"

publisher  = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

try:
    gmail.users().stop(userId="me").execute()
except googleapiclient.errors.HttpError as e:
    if e.resp.status != 400:   # 400 = no existing watch
        raise

try:
    publisher.get_topic(request={"topic": topic_full})
except NotFound:
    publisher.create_topic(name=topic_full)
    print(f"✓ created topic {topic_full}")

try:
    subscriber.create_subscription(
        name=sub_full,
        topic=topic_full,
        push_config=pubsub_v1.types.PushConfig(push_endpoint=args.push_endpoint),
    )
    print(f"✓ created push subscription {sub_full} → {args.push_endpoint}")
except AlreadyExists:
    # update the push endpoint in case it changed
    subscriber.modify_push_config(
        subscription=sub_full,
        push_config=pubsub_v1.types.PushConfig(push_endpoint=args.push_endpoint),
    )
    print(f"✓ subscription {sub_full} exists, push config ensured")

# ───────────────────── Gmail watch ───────────────────────
watch_request = {
    "topicName": topic_full,
}

resp = gmail.users().watch(userId="me", body=watch_request).execute()

STATE_FILE.write_text(json.dumps({"last_id": resp["historyId"]}))
print(f"✓ watch baseline saved to {STATE_FILE}")

print("📬 Gmail watch created:")
print(resp)
