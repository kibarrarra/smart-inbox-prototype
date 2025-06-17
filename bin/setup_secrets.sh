#!/bin/bash
# Setup remaining secrets in Secret Manager

# Extract client ID and secret from oauth_client.json
CLIENT_ID=$(jq -r '.installed.client_id' oauth_client.json)
CLIENT_SECRET=$(jq -r '.installed.client_secret' oauth_client.json)

# Create base64 encoded versions
echo -n "$CLIENT_ID" | base64 | gcloud secrets create gmail-client-id --data-file=- --project=smart-inbox-lab
echo -n "$CLIENT_SECRET" | base64 | gcloud secrets create gmail-client-secret --data-file=- --project=smart-inbox-lab

# For OpenAI key - you'll need to add this from .env
echo -n "$OPENAI_API_KEY" | gcloud secrets create openai-key --data-file=- --project=smart-inbox-lab

echo "✅ Secrets created. Now run: python main.py"