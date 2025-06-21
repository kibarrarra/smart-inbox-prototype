#!/usr/bin/env python3
"""
Manual OAuth token getter - no server, just URL
"""

import json
import base64
import pathlib
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
ROOT = pathlib.Path(__file__).resolve().parent
CLIENT_FILE = ROOT / "oauth_client.json"

def main():
    if not CLIENT_FILE.exists():
        print(f"❌ {CLIENT_FILE} not found")
        return
    
    print("🔗 Getting OAuth URL...")
    
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
    
    # Get the authorization URL
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    print(f"\n📋 STEP 1: Open this URL in your browser:")
    print(f"{auth_url}")
    print(f"\n📋 STEP 2: After authorizing, you'll be redirected to a localhost URL.")
    print(f"📋 STEP 3: Copy the ENTIRE URL from your browser address bar and paste it here.")
    print(f"\nWaiting for redirect URL...")
    
    redirect_url = input("Paste the full redirect URL here: ").strip()
    
    # Extract the authorization code from the URL
    if 'code=' not in redirect_url:
        print("❌ No authorization code found in URL")
        return
    
    # Parse the code
    code = redirect_url.split('code=')[1].split('&')[0]
    
    # Exchange code for token
    flow.fetch_token(code=code)
    creds = flow.credentials
    
    if not creds.refresh_token:
        print("❌ No refresh token received")
        return
    
    payload = {"refresh_token": creds.refresh_token}
    b64_payload = base64.b64encode(json.dumps(payload).encode()).decode()
    
    print(f"\n✅ SUCCESS! Here's your refresh token:")
    print(f"\n🔑 Base64 encoded for Secret Manager:")
    print(f"{b64_payload}")
    
    print(f"\n📋 To update Secret Manager, run:")
    print(f"gcloud secrets versions add gmail-refresh-token --data-file=- <<< '{b64_payload}'")
    
    # Also show raw JSON
    print(f"\n📋 Raw JSON:")
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    main()