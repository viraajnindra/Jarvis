"""Store the ElevenLabs API key in Windows Credential Manager.

Run: uv run scripts/store_elevenlabs_key.py
The key is read through a hidden prompt and never touches files, arguments, or
command history.
"""

import getpass

import keyring

SERVICE = "jarvis"
ACCOUNT = "elevenlabs_api_key"


def main() -> None:
    key = getpass.getpass("Paste ElevenLabs API key (input hidden): ").strip()
    if not key:
        print("No key entered, nothing stored.")
        return
    if not key.startswith("sk_"):
        print(
            "That is not an ElevenLabs secret API key. Use the full value shown "
            "when creating or rotating a key; it starts with 'sk_'. Nothing was stored."
        )
        return
    keyring.set_password(SERVICE, ACCOUNT, key)
    print(f"Stored under Credential Manager service '{SERVICE}' / account '{ACCOUNT}'.")


if __name__ == "__main__":
    main()
