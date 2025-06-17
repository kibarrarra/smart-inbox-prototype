#!/bin/bash
# dev.sh - Development mode with separate terminals

set -e

echo "🚀 Starting Smart Inbox in development mode (multi-terminal)..."

# Check prerequisites
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Run this from the project root directory"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "❌ No .env file found! Copy .env.example and add your OpenAI key"
    exit 1
fi

# Check for OAuth setup
if [ ! -f "oauth_client.json" ] && [ -z "$GOOGLE_CLIENT_ID_B64" ]; then
    echo "❌ Missing authentication setup!"
    echo "   Either:"
    echo "   1. Download oauth_client.json from Google Cloud Console"
    echo "   2. Set up environment variables (run scripts/get_refresh_token.py)"
    exit 1
fi

# Check for required tools
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok not found! Install from https://ngrok.com/download"
    exit 1
fi

# Check if port 8080 is available (if lsof is installed)
if command -v lsof &> /dev/null; then
    if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port 8080 is already in use. Kill the process or use a different port."
        echo "   To find the process: lsof -i :8080"
        exit 1
    fi
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
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

# Create scripts directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/dev_scripts"

# Create helper scripts for each terminal
cat > "$SCRIPT_DIR/dev_scripts/start_ngrok.sh" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
echo "🌐 Starting ngrok..."
echo "================================"
ngrok http 8080
EOF

cat > "$SCRIPT_DIR/dev_scripts/start_main.sh" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
source .venv/bin/activate 2>/dev/null || {
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing dependencies..."
    pip install -e .
}
echo "🐍 Starting FastAPI server..."
echo "================================"

# Check if OAuth is configured
if [ ! -f "oauth_client.json" ] && [ -z "\$GOOGLE_CLIENT_ID_B64" ]; then
    echo "⚠️  Warning: No OAuth credentials found!"
    echo "   To set up authentication, run: python scripts/get_refresh_token.py"
    echo ""
fi

echo "URL: http://localhost:8080"
echo "Docs: http://localhost:8080/docs"
echo ""
echo "Press Ctrl+C to restart server"
echo "================================"
# Use uvicorn with reload for auto-restart on code changes
python -m uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
EOF

cat > "$SCRIPT_DIR/dev_scripts/setup_watch.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || {
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing dependencies..."
    pip install -e .
}

# Ensure package is installed for imports
pip install -e . >/dev/null 2>&1

echo "📬 Gmail Watch Setup"
echo "================================"
echo "Waiting for ngrok to start..."
echo "⏳ Giving ngrok 5 seconds to initialize..."
sleep 5

# Get ngrok URL with retry logic
echo "🔍 Looking for ngrok URL..."
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('tunnels'):
        print(data['tunnels'][0]['public_url'])
except:
    pass
")

# Retry logic for ngrok URL
RETRY_COUNT=0
MAX_RETRIES=3
while [ -z "$NGROK_URL" ] && [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if [ $RETRY_COUNT -gt 0 ]; then
        echo "⏳ Retrying... (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 5
    fi
    
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('tunnels'):
        print(data['tunnels'][0]['public_url'])
except:
    pass
")
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ -z "$NGROK_URL" ]; then
    echo "❌ Could not find ngrok URL after $MAX_RETRIES attempts"
    echo "   Please ensure ngrok is running on port 8080"
    echo "   You can manually run: ngrok http 8080"
    exit 1
fi

echo "✅ Found ngrok URL: $NGROK_URL"

# Get project ID from environment or saved file
if [ -f ".env" ]; then
    source .env
fi

if [ -n "$GOOGLE_CLOUD_PROJECT" ]; then
    PROJECT_ID=$GOOGLE_CLOUD_PROJECT
    echo "Using project ID from .env: $PROJECT_ID"
elif [ -f ".last_project_id" ]; then
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

chmod +x "$SCRIPT_DIR/dev_scripts/start_ngrok.sh" "$SCRIPT_DIR/dev_scripts/start_main.sh" "$SCRIPT_DIR/dev_scripts/setup_watch.sh"

# Launch terminals based on what's available
case $TERMINAL in
    "windows-terminal")
        echo "🖥️  Opening Windows Terminal tabs..."
        # Open new tabs in Windows Terminal
        wt.exe -w 0 new-tab --title "Ngrok" --suppressApplicationTitle bash "$SCRIPT_DIR/dev_scripts/start_ngrok.sh" \; \
               new-tab --title "FastAPI Server" --suppressApplicationTitle bash "$SCRIPT_DIR/dev_scripts/start_main.sh" \; \
               new-tab --title "Gmail Watch" --suppressApplicationTitle bash "$SCRIPT_DIR/dev_scripts/setup_watch.sh"
        ;;
    
    "gnome-terminal")
        echo "🖥️  Opening GNOME Terminal tabs..."
        gnome-terminal \
            --tab --title="Ngrok" -- bash "$SCRIPT_DIR/dev_scripts/start_ngrok.sh" \
            --tab --title="FastAPI Server" -- bash "$SCRIPT_DIR/dev_scripts/start_main.sh" \
            --tab --title="Gmail Watch" -- bash "$SCRIPT_DIR/dev_scripts/setup_watch.sh"
        ;;
    
    "konsole")
        echo "🖥️  Opening Konsole tabs..."
        konsole --new-tab -e bash "$SCRIPT_DIR/dev_scripts/start_ngrok.sh" &
        konsole --new-tab -e bash "$SCRIPT_DIR/dev_scripts/start_main.sh" &
        konsole --new-tab -e bash "$SCRIPT_DIR/dev_scripts/setup_watch.sh" &
        ;;
    
    "xterm")
        echo "🖥️  Opening xterm windows..."
        xterm -title "Ngrok" -e bash "$SCRIPT_DIR/dev_scripts/start_ngrok.sh" &
        xterm -title "FastAPI Server" -e bash "$SCRIPT_DIR/dev_scripts/start_main.sh" &
        xterm -title "Gmail Watch" -e bash "$SCRIPT_DIR/dev_scripts/setup_watch.sh" &
        ;;
    
    *)
        # Check if tmux is available
        if command -v tmux &> /dev/null; then
            echo "🚀 Launching in tmux session..."
            echo ""
            
            # Kill existing session if it exists
            tmux kill-session -t smart-inbox 2>/dev/null || true
            
            # Create new tmux session with three panes
            tmux new-session -d -s smart-inbox -n main
            
            # Split window into three panes
            tmux split-window -h -t smart-inbox:main
            tmux split-window -v -t smart-inbox:main.0
            
            # Run commands in each pane
            tmux send-keys -t smart-inbox:main.0 "$SCRIPT_DIR/dev_scripts/start_ngrok.sh" C-m
            tmux send-keys -t smart-inbox:main.1 "$SCRIPT_DIR/dev_scripts/start_main.sh" C-m
            tmux send-keys -t smart-inbox:main.2 "sleep 8 && $SCRIPT_DIR/dev_scripts/setup_watch.sh" C-m
            
            # Set pane titles
            tmux select-pane -t smart-inbox:main.0 -T "Ngrok"
            tmux select-pane -t smart-inbox:main.1 -T "FastAPI Server"
            tmux select-pane -t smart-inbox:main.2 -T "Gmail Watch"
            
            # Enable pane titles
            tmux set -t smart-inbox pane-border-status top
            
            echo "✅ All services starting in tmux session 'smart-inbox'"
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "📺 TMUX SESSION RUNNING IN BACKGROUND"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            echo "View the session (choose one):"
            echo "  • tmux attach -t smart-inbox          # Take over this terminal"
            echo "  • tmux new-window -t smart-inbox \\; attach  # Open in new tmux window"
            echo ""
            echo "Other commands:"
            echo "  • tmux ls                             # List sessions"
            echo "  • tmux kill-session -t smart-inbox    # Stop all services"
            echo ""
            echo "📝 Tmux controls (when attached):"
            echo "  • Ctrl+B → Arrow keys = Navigate panes"
            echo "  • Ctrl+B → Z = Zoom/unzoom current pane"  
            echo "  • Ctrl+B → D = Detach from session"
            echo "  • Ctrl+B → C = Create new window"
            echo "  • Ctrl+B → N/P = Next/Previous window"
            echo ""
            echo "💡 TIP: Services are running! You can:"
            echo "  1. Keep this terminal for other work"
            echo "  2. Open a new terminal tab and run: tmux attach -t smart-inbox"
            echo "  3. Check if everything started: curl http://localhost:8080/healthz"
            echo ""
            
            # Check if we can open a new terminal window/tab
            if command -v gnome-terminal &> /dev/null; then
                read -p "Press Enter to open tmux in a new terminal, or Ctrl+C to keep it in background... "
                gnome-terminal -- tmux attach -t smart-inbox &
            elif command -v xterm &> /dev/null; then
                read -p "Press Enter to open tmux in a new terminal, or Ctrl+C to keep it in background... "
                xterm -e tmux attach -t smart-inbox &
            else
                echo "Press Enter to attach to tmux in this terminal, or Ctrl+C to keep it in background..."
                read
                tmux attach -t smart-inbox
            fi
        else
            echo "ℹ️  Running in headless/WSL mode - creating helper scripts"
            echo ""
            echo "💡 Tip: Install tmux for automatic terminal management: sudo apt install tmux"
            echo ""
            echo "✅ Helper scripts created in dev_scripts/"
            echo ""
            echo "Please run these in separate terminals:"
            echo ""
            echo "Terminal 1: ./dev_scripts/start_ngrok.sh"
            echo "Terminal 2: ./dev_scripts/start_main.sh"
            echo "Terminal 3: ./dev_scripts/setup_watch.sh"
            echo ""
            echo "💡 Tip: Run Terminal 1 first (ngrok), then Terminal 2 (server), then Terminal 3 (watch)"
        fi
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