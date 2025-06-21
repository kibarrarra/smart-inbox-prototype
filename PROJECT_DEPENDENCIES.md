# Project Dependencies

## Python Environment
- Python 3.8+
- Virtual environment at `.venv/`

## Required Libraries (Available)
✅ **OpenAI** - `openai` - For email classification using GPT models
✅ **FastAPI** - `fastapi` + `uvicorn` - Web server for push notifications  
✅ **Google APIs** - `google-api-python-client`, `google-auth`, `google-auth-httplib2` - Gmail integration
✅ **Google Cloud** - `google-cloud-secretmanager` - Secret management in production
✅ **Python-dotenv** - `.env` file loading for local development
✅ **Pathlib** - File path handling (built-in)
✅ **JSON** - Data parsing (built-in)
✅ **Base64** - Credential encoding (built-in)
✅ **Logging** - Built-in Python logging

## System Dependencies
✅ **ngrok** - Public tunnel for Gmail webhooks during development
✅ **curl** - HTTP testing (system command)

## Project Structure
- `src/` - Main application code
- `scripts/` - Utility scripts for setup
- `bin/` - Shell scripts for development
- `.env` - Local environment variables
- `pyproject.toml` - Package configuration

## Gmail API Setup Required
- OAuth client credentials in `oauth_client.json`
- Pub/Sub topic for push notifications
- Gmail API and Pub/Sub API enabled in Google Cloud Console

## Current System Status
- ✅ Email classification working with intelligent scoring (0.0-1.0)
- ✅ Four-tier labeling system: Critical (0.8+), Urgent (0.5+), Medium (0.4+), Digest (<0.4)
- ✅ Enhanced prompt with finance-specific context and examples
- ✅ Provider abstraction ready for Outlook/Graph API
- ✅ Stateless token refresh system for production deployment

## Next Development Areas
- Gmail watch integration testing
- Live email processing verification
- Prompt optimization based on real-world performance
- Additional label categories for specialized workflows