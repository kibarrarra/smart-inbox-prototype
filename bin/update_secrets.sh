#!/bin/bash
# Update existing secrets in Secret Manager with new OAuth credentials

set -e

echo "🔄 Updating Secret Manager with new OAuth credentials..."

# Check if oauth_client.json exists
if [ ! -f "oauth_client.json" ]; then
    echo "❌ oauth_client.json not found! Please download it first."
    exit 1
fi

# Extract client ID and secret from oauth_client.json
CLIENT_ID=$(jq -r '.installed.client_id' oauth_client.json)
CLIENT_SECRET=$(jq -r '.installed.client_secret' oauth_client.json)

if [ "$CLIENT_ID" = "null" ] || [ "$CLIENT_SECRET" = "null" ]; then
    echo "❌ Could not extract client credentials from oauth_client.json"
    echo "   Make sure it's a valid OAuth client file for Desktop application"
    exit 1
fi

echo "📝 Found credentials in oauth_client.json"
echo "   Client ID: ${CLIENT_ID:0:20}..."

# Update existing secrets (use --data-file=- to read from stdin)
echo "🔄 Updating gmail-client-id..."
echo -n "$CLIENT_ID" | base64 | gcloud secrets versions add gmail-client-id --data-file=- --project=smart-inbox-lab

echo "🔄 Updating gmail-client-secret..."
echo -n "$CLIENT_SECRET" | base64 | gcloud secrets versions add gmail-client-secret --data-file=- --project=smart-inbox-lab

echo ""
echo "✅ Updated OAuth credentials in Secret Manager!"
echo ""
echo "🔑 Now you need to get a new refresh token:"
echo "   python scripts/get_refresh_token.py"
echo ""
echo "   This will output a new GMAIL_REFRESH_B64 value."
echo "   Copy that value and run:"
echo "   echo 'PASTE_B64_VALUE_HERE' | base64 -d | gcloud secrets versions add gmail-refresh-token --data-file=- --project=smart-inbox-lab"