"""Store a Canvas access token + set the Canvas base URL.

Get a token: Canvas -> Account -> Settings -> Approved Integrations ->
+ New Access Token. Paste it below (input hidden).

Run: uv run scripts/setup_canvas.py
"""

import getpass
import sys
from pathlib import Path

import keyring

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402


def main() -> None:
    print(f"Current Canvas URL: {config.CANVAS_BASE_URL or '(unset)'}")
    print("Set JARVIS_CANVAS_URL in backend/.env, e.g. https://yourschool.instructure.com")
    token = getpass.getpass("Paste Canvas access token (hidden): ").strip()
    if not token:
        print("No token entered, nothing stored.")
        return
    keyring.set_password(config.KEYRING_SERVICE, "canvas_token", token)
    print("Stored canvas_token in Credential Manager.")
    if not config.CANVAS_BASE_URL:
        print("WARNING: JARVIS_CANVAS_URL not set — add it to backend/.env before syncing.")


if __name__ == "__main__":
    main()
