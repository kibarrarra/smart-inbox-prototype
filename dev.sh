#!/bin/bash
# dev.sh - Development mode with separate terminals

set -e

echo "🚀 Starting Smart Inbox in development mode (multi-terminal)..."

# Check prerequisites
if [ ! -f "main.py" ]; then
    echo "❌ Error: Run this from the project root directory"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "❌ No .env file found! Copy .env.example and add your OpenAI key"
    exit 1
fi

if [ ! -f "oauth_client.json" ]; then
    echo "❌ Missing oauth_client.json - download from Google Cloud Console"
    exit 1
fi

# Detect terminal emulator
detect_terminal() {
    if command -v wt.exe &> /dev/null; then
        echo "windows-terminal"
    elif command -v gnome-terminal &> /dev/null; then
        echo "gnome-terminal"
    elif command -v konsole &> /dev/null; then
        echo "konsole"
    elif command -v xterm &> /dev/null; then
        echo "xterm"
    else
        echo "none"
    fi
}

TERMINAL=$(detect_terminal)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create helper scripts for each terminal
cat > /tmp/start_ngrok.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "🌐 Starting ngrok..."
echo "================================"
ngrok http 8080
EOF

cat > /tmp/start_main.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || {
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
}
echo "🐍 Starting FastAPI server..."
echo "================================"
echo "URL: http://localhost:8080"
echo "Docs: http://localhost:8080/docs"
echo ""
echo "Press Ctrl+C to restart server"
echo "================================"
python main.py
EOF

cat > /tmp/setup_watch.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || {
    python3 -m venv .venv
    source .venv/bin/activate
}

echo "📬 Gmail Watch Setup"
echo "================================"
echo "Waiting for ngrok to start..."
sleep 5

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('tunnels'):
        print(data['tunnels'][0]['public_url'])
except:
    pass
")

if [ -z "$NGROK_URL" ]; then
    echo "❌ Ngrok not running yet. Please:"
    echo "1. Wait for ngrok to start in Terminal 1"
    echo "2. Press Enter to retry"
    read -p "Press Enter when ngrok is running..."
    
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data['tunnels'][0]['public_url'])
")
fi

echo "✅ Found ngrok URL: $NGROK_URL"

# Get project ID
if [ -f ".last_project_id" ]; then
    PROJECT_ID=$(cat .last_project_id)
    echo "Using saved project ID: $PROJECT_ID"
else
    echo -n "Enter your GCP project ID: "
    read PROJECT_ID
    echo $PROJECT_ID > .last_project_id
fi

echo ""
echo "Setting up Gmail watch..."
python scripts/create_watch.py \
    --project="$PROJECT_ID" \
    --topic=gmail-watch-topic \
    --push-endpoint="$NGROK_URL/gmail/push"

echo ""
echo "✅ Watch setup complete!"
echo ""
echo "📧 Send yourself an email to test"
echo "👀 Watch Terminal 2 for processing logs"
echo ""
echo "This terminal can be closed now."
EOF

chmod +x /tmp/start_ngrok.sh /tmp/start_main.sh /tmp/setup_watch.sh

# Copy scripts to project directory
cp /tmp/start_ngrok.sh "$SCRIPT_DIR/"
cp /tmp/start_main.sh "$SCRIPT_DIR/"
cp /tmp/setup_watch.sh "$SCRIPT_DIR/"

# Launch terminals based on what's available
case $TERMINAL in
    "windows-terminal")
        echo "🖥️  Opening Windows Terminal tabs..."
        # Open new tabs in Windows Terminal
        wt.exe -w 0 new-tab --title "Ngrok" --suppressApplicationTitle bash "$SCRIPT_DIR/start_ngrok.sh" \; \
               new-tab --title "FastAPI Server" --suppressApplicationTitle bash "$SCRIPT_DIR/start_main.sh" \; \
               new-tab --title "Gmail Watch" --suppressApplicationTitle bash "$SCRIPT_DIR/setup_watch.sh"
        ;;
    
    "gnome-terminal")
        echo "🖥️  Opening GNOME Terminal tabs..."
        gnome-terminal \
            --tab --title="Ngrok" -- bash "$SCRIPT_DIR/start_ngrok.sh" \
            --tab --title="FastAPI Server" -- bash "$SCRIPT_DIR/start_main.sh" \
            --tab --title="Gmail Watch" -- bash "$SCRIPT_DIR/setup_watch.sh"
        ;;
    
    "konsole")
        echo "🖥️  Opening Konsole tabs..."
        konsole --new-tab -e bash "$SCRIPT_DIR/start_ngrok.sh" &
        konsole --new-tab -e bash "$SCRIPT_DIR/start_main.sh" &
        konsole --new-tab -e bash "$SCRIPT_DIR/setup_watch.sh" &
        ;;
    
    "xterm")
        echo "🖥️  Opening xterm windows..."
        xterm -title "Ngrok" -e bash "$SCRIPT_DIR/start_ngrok.sh" &
        xterm -title "FastAPI Server" -e bash "$SCRIPT_DIR/start_main.sh" &
        xterm -title "Gmail Watch" -e bash "$SCRIPT_DIR/setup_watch.sh" &
        ;;
    
    *)
        echo "❌ No supported terminal found!"
        echo ""
        echo "Please run these commands in separate terminals:"
        echo ""
        echo "Terminal 1: ngrok http 8080"
        echo "Terminal 2: source .venv/bin/activate && python main.py"
        echo "Terminal 3: ./setup_watch.sh"
        exit 1
        ;;
esac

echo ""
echo "✅ Development environment starting in separate terminals!"
echo ""
echo "Terminal 1: Ngrok tunnel"
echo "Terminal 2: FastAPI server (restart anytime with Ctrl+C)"
echo "Terminal 3: Gmail watch setup (run once)"
echo ""
echo "💡 Tip: You can close Terminal 3 after watch setup"
echo "💡 Tip: Restart only Terminal 2 when changing main.py" 