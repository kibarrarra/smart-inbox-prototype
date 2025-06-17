# dev.sh Fix Experiment

## Goal with this Change - Impact Focus

The goal is to ensure the development environment can be spun up reliably with `dev.sh`, enabling rapid iteration on the smart inbox prototype. The impact:

1. **Developer Productivity**: A working dev.sh means developers can start coding immediately without wrestling with setup
2. **Debugging Speed**: Separate terminals for each component allow real-time monitoring of ngrok tunnels, server logs, and Gmail webhooks
3. **Reduced Friction**: New team members can onboard quickly with a single command
4. **Error Recovery**: When something breaks, developers can restart individual components without affecting others

## What I've Learned from Existing Code

### Architecture Changes
1. **Config Refactor**: The project moved from file-based auth (`token.json`) to environment/secret-based auth
   - `config.py` now handles all configuration with a priority order: env vars → .env → Google Secret Manager
   - OAuth tokens are built on-the-fly from refresh tokens stored as base64
   - No more dependency on `token.json` file

2. **Missing Dependencies**:
   - `dev.sh` references `requirements.txt` but the project uses `pyproject.toml`
   - Need to use `pip install -e .` instead of `pip install -r requirements.txt`

3. **Authentication Flow**:
   - The new system expects base64-encoded credentials in env vars:
     - `GOOGLE_CLIENT_ID_B64`
     - `GOOGLE_CLIENT_SECRET_B64`
     - `GMAIL_REFRESH_B64`
   - These can be generated using `scripts/get_refresh_token.py`

4. **WSL/Headless Considerations**:
   - We're in WSL without GUI access
   - Terminal detection in dev.sh won't work properly
   - Need to handle the "none" terminal case better

## Surgical Plan of Attack

1. **Fix pip install command** in `/tmp/start_main.sh`:
   - Change `pip install -r requirements.txt` to `pip install -e .`

2. **Add config validation** before starting servers:
   - Check if required env vars or oauth_client.json exist
   - Provide clear instructions if missing

3. **Improve terminal handling** for WSL:
   - Make the fallback case more actionable
   - Create persistent helper scripts instead of temp files

4. **Add pre-flight checks**:
   - Verify ngrok is installed
   - Check if port 8080 is available
   - Ensure .venv can be created

5. **Fix watch setup script**:
   - Add better error handling for ngrok URL detection
   - Handle the case where config.py credentials aren't set up yet

Let me implement these fixes...

## Attempted Solution

I've made the following changes to dev.sh:

1. **Fixed pip install command**:
   - Changed `pip install -r requirements.txt` to `pip install -e .` to use pyproject.toml

2. **Added comprehensive pre-flight checks**:
   - Check for either oauth_client.json OR environment variables (supporting both auth methods)
   - Verify ngrok is installed before attempting to use it
   - Check if port 8080 is available (with graceful handling if lsof isn't installed)

3. **Improved WSL/headless terminal handling**:
   - Created persistent helper scripts in `dev_scripts/` directory instead of /tmp
   - Made the "no terminal found" case helpful instead of an error
   - Scripts now properly cd to project root instead of relative paths

4. **Added OAuth configuration warnings**:
   - The FastAPI startup script now warns if OAuth isn't configured
   - Provides helpful guidance to run scripts/get_refresh_token.py

5. **Fixed script paths**:
   - All embedded scripts now use absolute paths via $SCRIPT_DIR
   - Helper scripts are organized in dev_scripts/ subdirectory
   - Scripts persist between runs for manual execution

The key improvements:
- **Compatibility**: Works with both old (oauth_client.json) and new (config.py) auth methods
- **Robustness**: Better error handling and pre-flight checks
- **WSL-friendly**: Gracefully handles headless environments
- **Developer-friendly**: Clear error messages with actionable next steps

To test:
1. Run `./dev.sh` in your terminal
2. It should create helper scripts in `dev_scripts/`
3. Run each script in a separate terminal as instructed

## Enhancement: Automatic Terminal Spawning with tmux

Since you're in WSL and tmux is installed, I've added automatic terminal spawning:

**How it works:**
1. When you run `./dev.sh`, it detects tmux is available
2. Creates a tmux session called "smart-inbox" with 3 panes
3. Automatically starts ngrok, FastAPI server, and Gmail watch in separate panes
4. Attaches you to the session so you can see all outputs

**tmux benefits:**
- **Automatic setup** - No need to manually open terminals
- **Split view** - See all services running simultaneously
- **Persistent sessions** - Detach with Ctrl+B, D and reattach later
- **Easy management** - Kill all with: `tmux kill-session -t smart-inbox`

**tmux controls:**
- `Ctrl+B` → Arrow keys = Navigate between panes
- `Ctrl+B` → `Z` = Zoom in/out of current pane
- `Ctrl+B` → `D` = Detach (services keep running)
- `tmux attach -t smart-inbox` = Reattach to session

The script gracefully falls back to manual mode if tmux isn't available.