#!/bin/bash
# Manual verification commands you can run to check OAuth status

echo "=== Gmail OAuth Verification Commands ==="
echo "Run these commands yourself to verify the token status:"
echo

echo "1. Check your Google Account permissions:"
echo "   Open: https://myaccount.google.com/permissions"
echo "   Look for your app (likely 'Quickstart' or similar)"
echo

echo "2. Test the raw OAuth refresh call:"
echo "   Run this curl command to test token refresh directly:"
echo

# Extract credentials and show the curl command
source .venv/bin/activate
python3 << 'EOF'
import sys
sys.path.append('src')
from src.config import cfg
import json, base64

try:
    # Decode credentials
    refresh_data = json.loads(base64.b64decode(cfg.REFRESH_B64))
    rt = refresh_data['refresh_token']
    client_id = base64.b64decode(cfg.CLIENT_ID_B64).decode()
    client_secret = base64.b64decode(cfg.CLIENT_SECRET_B64).decode()
    
    print(f"""
curl -X POST https://oauth2.googleapis.com/token \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "grant_type=refresh_token" \\
  -d "refresh_token={rt}" \\
  -d "client_id={client_id}" \\
  -d "client_secret={client_secret}"
""")
    
    print("3. If that curl succeeds, your token is valid!")
    print("   If it fails with 'invalid_grant', then the token is indeed revoked.")
    print()
    
except Exception as e:
    print(f"Error extracting credentials: {e}")
EOF

echo "4. Check your Google Cloud Console OAuth app:"
echo "   https://console.cloud.google.com/apis/credentials?project=${GOOGLE_CLOUD_PROJECT}"
echo "   Verify the OAuth client is still active"
echo

echo "5. Check if Gmail API is enabled:"
echo "   https://console.cloud.google.com/apis/library/gmail.googleapis.com?project=${GOOGLE_CLOUD_PROJECT}"
echo

echo "6. Test with a simple Gmail API call (if curl above worked):"
echo "   Save the access_token from the curl response, then:"
echo "   curl -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' https://gmail.googleapis.com/gmail/v1/users/me/profile"