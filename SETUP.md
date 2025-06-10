# Gmail Service Account Setup Guide

## Current Issue
The server is running but failing with authentication errors. This is because the service account needs proper configuration for Gmail API access.

## Requirements

1. **Enable Domain-Wide Delegation**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Navigate to IAM & Admin > Service Accounts
   - Find your service account (the one in `sa.json`)
   - Click on it and go to "Details" tab
   - Check "Enable G Suite Domain-wide Delegation"
   - Save

2. **Authorize in Google Workspace Admin**
   - Go to [Google Admin Console](https://admin.google.com)
   - Navigate to Security > API Controls > Domain-wide delegation
   - Click "Add new"
   - Enter the Client ID from your service account (found in `sa.json` as `client_id`)
   - Add this OAuth scope: `https://www.googleapis.com/auth/gmail.modify`
   - Save

3. **Verify Service Account File**
   - Your `sa.json` should have these fields:
     - `type`: "service_account"
     - `private_key`
     - `client_email`
     - `client_id`

4. **Test the Setup**
   ```bash
   # With virtual environment activated
   python -c "
   from main import provider
   service = provider._get_service()
   profile = service.users().getProfile(userId='me').execute()
   print(f'Success! History ID: {profile[\"historyId\"]}')
   "
   ```

## Troubleshooting

- **"unauthorized_client" error**: Domain-wide delegation not enabled or not authorized in Admin console
- **"failedPrecondition" error**: Service account not authorized for the user specified in GMAIL_USER
- Make sure `GMAIL_USER` in `.env` matches a valid user in your Google Workspace domain

## For Testing Without Domain-Wide Delegation

If you're testing with a personal Gmail account, you'll need to use OAuth2 flow instead of service accounts. Service accounts with domain-wide delegation only work with Google Workspace (formerly G Suite) accounts. 