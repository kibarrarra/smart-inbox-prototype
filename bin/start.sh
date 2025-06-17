#!/bin/bash
# start.sh - One command to rule them all 🚀

set -e  # Exit on error

echo "🚀 Starting Smart Inbox development environment..."

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Run this from the project root directory"
    exit 1
fi

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

echo "🐍 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies if needed
if ! python -c "import openai" 2>/dev/null; then
    echo "📚 Installing dependencies..."
    pip install -e .
fi

# Check for required files
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found! Creating template..."
    cat > .env << EOF
OPENAI_API_KEY=sk-YOUR-KEY-HERE
OPENAI_MODEL=gpt-4o-mini
LABEL_CRITICAL=AI/Critical
LABEL_DIGEST=AI/DigestQueue
IMPORTANCE_THRESHOLD=0.5
EOF
    echo "❌ Please edit .env and add your OpenAI API key!"
    exit 1
fi

if [ ! -f "oauth_client.json" ]; then
    echo "❌ Missing oauth_client.json - download from Google Cloud Console"
    exit 1
fi

# Check if token.json exists, if not create it
if [ ! -f "token.json" ]; then
    echo "🔐 No Gmail auth token found. Running authentication..."
    python scripts/create_oauth_token.py
fi

# Kill any existing processes
echo "🔪 Killing any existing processes..."
pkill -f "python.*src.main" || true
pkill -f ngrok || true

# Start the FastAPI server in background
echo "🌐 Starting FastAPI server..."
python -m src.main &
SERVER_PID=$!

# Give server time to start
sleep 3

# Check if server is running
if ! curl -s http://localhost:8080/healthz > /dev/null; then
    echo "❌ Server failed to start. Check the logs above."
    exit 1
fi

# Start ngrok
echo "🌐 Starting ngrok tunnel..."
ngrok http 8080 > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for ngrok to start and extract URL
echo "⏳ Waiting for ngrok to start..."
sleep 4

# Get ngrok URL using the API
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data['tunnels']:
    print(data['tunnels'][0]['public_url'])
else:
    print('ERROR')
")

if [ "$NGROK_URL" = "ERROR" ] || [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL. Check if ngrok is installed and running."
    kill $SERVER_PID
    exit 1
fi

echo "✅ Ngrok URL: $NGROK_URL"

# Get project ID from previous runs or ask
if [ -f ".last_project_id" ]; then
    PROJECT_ID=$(cat .last_project_id)
    echo "📋 Using previous project ID: $PROJECT_ID"
else
    echo -n "Enter your GCP project ID: "
    read PROJECT_ID
    echo $PROJECT_ID > .last_project_id
fi

# Update the Gmail watch with the new URL
echo "📬 Setting up Gmail watch..."
python scripts/create_watch.py \
    --project="$PROJECT_ID" \
    --topic=gmail-watch-topic \
    --push-endpoint="$NGROK_URL/gmail/push" || {
    echo "⚠️  Watch creation failed, but server is still running"
}

echo ""
echo "✅ Everything is running!"
echo ""
echo "📊 Server logs: tail -f logs (in another terminal)"
echo "🌐 Ngrok URL: $NGROK_URL"
echo "📚 API docs: http://localhost:8080/docs"
echo "🔍 Ngrok inspector: http://localhost:4040"
echo ""
echo "📧 Send yourself an email to test!"
echo ""
echo "Press Ctrl+C to stop everything..."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $SERVER_PID 2>/dev/null || true
    kill $NGROK_PID 2>/dev/null || true
    pkill -f ngrok || true
    echo "✅ Cleanup complete"
}

trap cleanup EXIT

# Wait for Ctrl+C
wait $SERVER_PID 