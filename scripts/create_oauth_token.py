#!/usr/bin/env python3
"""
Generate OAuth token for production deployment.
Run this locally before deploying to Cloud Run.
"""

import pathlib
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

def main():
    SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
    root = pathlib.Path(__file__).parent.parent
    
    # Use the same paths as main.py
    oauth_client_file = root / "oauth_client.json"
    token_file = root / "token.json"
    
    if not oauth_client_file.exists():
        print(f"Error: {oauth_client_file} not found!")
        print("Please download OAuth client credentials from Google Cloud Console.")
        sys.exit(1)
    
    print("Generating OAuth token for Gmail API...")
    
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        print("Found existing token.json")
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Starting OAuth flow...")
            print("A browser window will open for authentication.")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(oauth_client_file), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save the credentials
        token_file.write_text(creds.to_json())
        print(f"✅ Token saved to {token_file}")
    else:
        print("✅ Token is already valid")
    
    print("\nIMPORTANT for production deployment:")
    print("1. Include token.json in your Docker image or deployment")
    print("2. The token will expire eventually and need refreshing")
    print("3. Consider using Cloud Scheduler to refresh the token periodically")

if __name__ == "__main__":
    main() 