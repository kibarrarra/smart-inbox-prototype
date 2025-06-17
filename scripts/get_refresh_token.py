#!/usr/bin/env python3
"""
get_refresh_token.py
--------------------
Interactive helper for personal-Gmail deployments
( no Workspace admin, no service-account impersonation ).

• Uses an OAuth “Desktop App” client (client-id / client-secret)
• Scope: https://www.googleapis.com/auth/gmail.modify  (read + label)
• Prints a tiny JSON payload:   {"refresh_token": "...."}
  ─ store that in Secret Manager, not on disk.

Run once per mailbox, then delete the script.
"""

import base64
import json
import pathlib
import sys
import textwrap
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
ROOT = pathlib.Path(__file__).resolve().parent.parent
CLIENT_FILE = ROOT / "oauth_client.json"      # downloaded from GCP → “Desktop App”

def main() -> None:
    if not CLIENT_FILE.exists():
        sys.exit(f"❌  {CLIENT_FILE} not found — download OAuth client JSON first.")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_FILE), SCOPES
    )
    # For WSL/headless environments - manual URL copy/paste
    creds = flow.run_local_server(port=0, prompt="consent", open_browser=False)

    refresh_token = creds.refresh_token
    if not refresh_token:
        sys.exit("❌ No refresh-token received (did you tick 'Allow offline access'?).")

    payload = {"refresh_token": refresh_token}
    print("\n🔑  COPY the line below into your secret store:\n")
    b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    print(f"echo '{b64}' | gcloud secrets versions add gmail-refresh-token --data-file=-")
    print("\n📋  (or paste the JSON into AWS Secrets Manager / HashiCorp Vault):")
    print(json.dumps(payload, indent=2))
    print(
        textwrap.dedent(
            f"""
            Save your **client-id** and **client-secret** the same way
            (base64-encode and push to Secret Manager as gmail-client-id / gmail-client-secret).

            In your FastAPI app you’ll then load them with:
                cid  = base64.b64decode(os.environ["GMAIL_CLIENT_ID_B64"]).decode()
                csec = base64.b64decode(os.environ["GMAIL_CLIENT_SECRET_B64"]).decode()
                rtok = json.loads(base64.b64decode(os.environ["GMAIL_REFRESH_B64"]))["refresh_token"]
            and build Credentials() in memory — no token.json ever written.
            """
        ).strip()
    )

if __name__ == "__main__":
    main()
