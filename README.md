# Smart Inbox Prototype

A minimal event-driven smart inbox that receives Gmail push notifications via Pub/Sub and classifies emails using AI.

## 🚀 Super Quick Start

```bash
# First time setup
git clone <repo>
cd smart-inbox-prototype
cp .env.example .env          # Add your OpenAI key
# Add oauth_client.json from Google Cloud Console

# Start everything with one command!
./start.sh
```

That's it! The script handles everything:
- ✅ Virtual environment
- ✅ Dependencies  
- ✅ Gmail authentication
- ✅ Server startup
- ✅ Ngrok tunnel
- ✅ Watch registration

## Architecture

```
Gmail → Push Notification → Pub/Sub → FastAPI Handler → OpenAI Classifier → Gmail Labels
```

**Future**: Will support Outlook/Graph webhooks and serverless deployment (OpenFaaS/Knative).

## First Time Setup

### 1. Google Cloud Setup
1. Create a GCP project at https://console.cloud.google.com
2. Enable APIs:
   - Gmail API
   - Pub/Sub API
3. Create OAuth 2.0 credentials:
   - Go to APIs & Services → Credentials
   - Create Credentials → OAuth client ID
   - Application type: Desktop app
   - Download as `oauth_client.json` to project root

### 2. Pub/Sub Permissions
In Cloud Console → Pub/Sub → Topics:
1. Create topic (or let the script create it)
2. Add member `gmail-api-push@system.gserviceaccount.com`
3. Role: `Pub/Sub Publisher`

### 3. Environment Setup
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Daily Development Workflow

```bash
# Just run this every time!
./start.sh

# In another terminal, watch logs:
tail -f *.log
```

## Manual Setup (if start.sh doesn't work)

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Authenticate Gmail (first time)
python scripts/create_oauth_token.py

# 4. Start server
python main.py

# 5. In another terminal, start ngrok
ngrok http 8080

# 6. Set up Gmail watch
python scripts/create_watch.py \
  --project=YOUR_PROJECT \
  --topic=gmail-watch-topic \
  --push-endpoint=https://YOUR-NGROK.ngrok-free.app/gmail/push
```

## How It Works

1. **Gmail Watch** - Monitors your inbox for new emails
2. **Push Notifications** - Gmail sends notifications to Pub/Sub
3. **HTTP Handler** - FastAPI endpoint receives and processes notifications
4. **AI Classification** - OpenAI scores email importance (0-1)
5. **Auto-labeling** - Applies "AI/Critical" or "AI/DigestQueue" labels

## Troubleshooting

### start.sh issues
- Make sure you have `ngrok` installed: `brew install ngrok` (Mac) or download from ngrok.com
- Check `.env` has your OpenAI key
- Ensure `oauth_client.json` exists

### No emails being processed
- Send yourself a test email
- Check if labels exist in Gmail: AI/Critical and AI/DigestQueue
- Look for errors in the terminal

### Authentication errors
- Delete `token.json` and run `./start.sh` again
- Make sure oauth_client.json is valid

## Environment Variables

```env
OPENAI_API_KEY=sk-...          # Required
OPENAI_MODEL=gpt-4o-mini       # Optional
LABEL_CRITICAL=AI/Critical     # Gmail label for important emails
LABEL_DIGEST=AI/DigestQueue    # Gmail label for non-urgent emails  
IMPORTANCE_THRESHOLD=0.5       # Score threshold (0-1)
```

## Files Created

- `token.json` - Gmail OAuth token (git-ignored)
- `watch_state.json` - Tracks last processed email
- `missing_messages.log` - Logs any emails that couldn't be fetched
- `.last_project_id` - Remembers your GCP project

## Production Deployment

For production/SaaS deployment:

1. **Pre-generate token.json** locally first
2. **Include in deployment** (Docker image, etc.)
3. **Set up token refresh** - OAuth tokens expire
4. **Use stable URL** instead of ngrok
5. **Configure monitoring** for push failures

## License

MIT
