# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Quick Start (Single Command)**
```bash
./start.sh
```
This handles everything: venv setup, dependencies, OAuth, server startup, ngrok tunnel, and Gmail watch registration.

**Development Mode (Multi-Terminal)**
```bash
./dev.sh
```
Opens separate terminals for ngrok, FastAPI server, and Gmail watch setup.

**Manual Commands**
```bash
# Setup environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Authentication (first time)
python scripts/create_oauth_token.py

# Start server
python main.py

# Setup Gmail watch (in another terminal)
python scripts/create_watch.py --project=YOUR_PROJECT --topic=gmail-watch-topic --push-endpoint=https://YOUR-NGROK.ngrok-free.app/gmail/push
```

**Health Check**
```bash
curl http://localhost:8080/healthz
```

## Architecture Overview

This is an event-driven email classification system with a simple flow:
```
Gmail → Push Notification → Pub/Sub → FastAPI Handler → OpenAI Classifier → Gmail Labels
```

### Key Components

1. **main.py** - Single-file FastAPI application (~400 LOC)
   - Handles Gmail push notifications via `/gmail/push` endpoint
   - Uses OpenAI to score email importance (0-1 scale)
   - Automatically applies labels: "AI/Critical" or "AI/DigestQueue"
   - Maintains processing state in `watch_state.json`

2. **State Management** - Uses `shared_constants.py`
   - `STATE_FILE` = `watch_state.json` - tracks last processed Gmail historyId
   - Prevents duplicate processing and handles server restarts gracefully

3. **Provider Pattern** - Extensible email provider architecture
   - `GmailProvider` - fully implemented with OAuth2 authentication
   - `OutlookProvider` - stub for future Microsoft Graph integration

4. **Authentication Flow**
   - Uses OAuth2 with `oauth_client.json` (from Google Cloud Console)
   - Stores tokens in `token.json` (auto-refreshed)
   - Supports both interactive and production deployment modes

### Important Files

- `oauth_client.json` - OAuth2 client credentials (from Google Cloud Console)
- `token.json` - Gmail API access token (auto-generated)
- `.env` - Environment variables (OpenAI key, labels, thresholds)
- `watch_state.json` - Processing checkpoint
- `missing_messages.log` - Logs inaccessible messages for investigation

## Configuration

Required environment variables in `.env`:
```bash
OPENAI_API_KEY=sk-...          # Required
OPENAI_MODEL=gpt-4o-mini       # Optional, defaults to gpt-4o-mini
LABEL_CRITICAL=AI/Critical     # Gmail label for important emails
LABEL_DIGEST=AI/DigestQueue    # Gmail label for non-urgent emails
IMPORTANCE_THRESHOLD=0.5       # Classification threshold (0-1)
```

## Google Cloud Setup Requirements

1. **APIs to Enable**
   - Gmail API
   - Pub/Sub API

2. **OAuth2 Credentials**
   - Create OAuth client ID (Desktop application type)
   - Download as `oauth_client.json`

3. **Pub/Sub Permissions**
   - Add `gmail-api-push@system.gserviceaccount.com` as Publisher to topic

## Development Notes

- **No Testing Framework** - The codebase doesn't include tests
- **Single Responsibility** - Each provider handles one email service
- **Error Handling** - Gracefully handles deleted/inaccessible messages
- **Production Ready** - Includes health checks and proper OAuth token management
- **Logging** - Comprehensive logging for debugging push notifications

## Common Issues

- **Authentication Errors**: Delete `token.json` and re-run authentication
- **Missing Messages**: Check `missing_messages.log` for emails that couldn't be fetched
- **Ngrok Issues**: Ensure ngrok is installed and accessible in PATH
- **Watch Failures**: Verify Pub/Sub permissions and topic exists

## Production Deployment

1. Pre-generate `token.json` locally using `scripts/create_oauth_token.py`
2. Include `token.json` in deployment (Docker image, etc.)
3. Use stable HTTPS URL instead of ngrok
4. Set up token refresh mechanism (OAuth tokens expire)
5. Configure monitoring for push notification failures