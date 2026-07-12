"""Store a Discord bot token.

Setup: discord.com/developers -> New Application -> Bot -> Reset Token (copy it).
Invite the bot to YOUR server with the "Send Messages" scope. Never automate a
normal user account — bots only.

Run: uv run scripts/setup_discord.py
"""

import getpass
import sys
from pathlib import Path

import keyring

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402


def main() -> None:
    token = getpass.getpass("Paste Discord bot token (hidden): ").strip()
    if not token:
        print("No token entered, nothing stored.")
        return
    keyring.set_password(config.KEYRING_SERVICE, "discord_bot_token", token)
    print("Stored discord_bot_token in Credential Manager.")


if __name__ == "__main__":
    main()
