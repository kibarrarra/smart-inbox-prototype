# Setting up OAuth in smart-inbox-lab Project

## Steps to create OAuth credentials in smart-inbox-lab:

1. **Go to Google Cloud Console**
   - Navigate to: https://console.cloud.google.com
   - Make sure `smart-inbox-lab` is selected in the project dropdown

2. **Enable Gmail API** (if not already enabled)
   ```bash
   gcloud services enable gmail.googleapis.com --project=smart-inbox-lab
   ```

3. **Create OAuth Consent Screen** (if not already done)
   - Go to "APIs & Services" → "OAuth consent screen"
   - Choose "External" (or "Internal" if using Google Workspace)
   - Fill in required fields:
     - App name: Smart Inbox Prototype
     - User support email: your email
     - Developer contact: your email
   - Add scope: `https://www.googleapis.com/auth/gmail.modify`
   - Add your email as a test user

4. **Create OAuth 2.0 Client ID**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop app"
   - Name: "Smart Inbox CLI"
   - Download the JSON file

5. **Replace oauth_client.json**
   ```bash
   # Backup old file
   mv oauth_client.json oauth_client_old_project.json
   
   # Copy new downloaded file
   cp ~/Downloads/client_secret_*.json oauth_client.json
   ```

6. **Get new refresh token**
   ```bash
   # This will use the new OAuth client
   python scripts/get_refresh_token.py
   ```

7. **Update environment variables**
   The script will output new base64-encoded values. Update your .env or secrets with:
   - GOOGLE_CLIENT_ID_B64
   - GOOGLE_CLIENT_SECRET_B64
   - GMAIL_REFRESH_B64

## Quick command to verify project setup:

```bash
gcloud config set project smart-inbox-lab
gcloud services list --enabled | grep -E "(gmail|pubsub)"
```

Should show:
- gmail.googleapis.com
- pubsub.googleapis.com

## After setup is complete:
1. Delete this file
2. Re-run `./bin/dev.sh`
3. The watch should now work with smart-inbox-lab project