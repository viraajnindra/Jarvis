"""One-time Gmail OAuth: run the consent flow, store the refresh token.

Setup:
1. console.cloud.google.com -> create/select a project -> enable the Gmail API.
2. APIs & Services -> Credentials -> Create OAuth client ID -> Desktop app.
3. Download the client secret JSON, save it as backend/data/gmail_client_secret.json.
4. OAuth consent screen -> add your Gmail as a Test user (keeps it free, no verification).

Run: uv run scripts/setup_gmail.py
Scope is gmail.send only — Jarvis can send, never read your mailbox.
"""

import sys
from pathlib import Path

import keyring

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CLIENT_SECRET = config.DATA_DIR / "gmail_client_secret.json"


def main() -> None:
    if not CLIENT_SECRET.exists():
        print(f"Missing {CLIENT_SECRET}")
        print("Download an OAuth 'Desktop app' client secret and save it there first.")
        return
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0)  # opens a browser, catches the redirect
    keyring.set_password(config.KEYRING_SERVICE, "gmail_oauth", creds.to_json())
    print("Stored gmail_oauth (refresh token) in Credential Manager.")
    print("gmail_send is now available. The client secret file can stay for future re-auth.")


if __name__ == "__main__":
    main()
