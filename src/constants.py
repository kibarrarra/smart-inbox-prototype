# shared_constants.py  (or top of both files)

from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent          # …/smart-inbox-prototype
STATE_FILE   = PROJECT_ROOT / "watch_state.json"        # single source of truth