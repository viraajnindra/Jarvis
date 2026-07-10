"""Store the Gemini API key in Windows Credential Manager.

Run: uv run scripts/store_gemini_key.py
The key is read via a hidden prompt and never touches files, args, or history.
"""

import getpass

import keyring

SERVICE = "jarvis"
ACCOUNT = "gemini_api_key"


def main() -> None:
    key = getpass.getpass("Paste Gemini API key (input hidden): ").strip()
    if not key:
        print("No key entered, nothing stored.")
        return
    keyring.set_password(SERVICE, ACCOUNT, key)
    print(f"Stored under Credential Manager service '{SERVICE}' / account '{ACCOUNT}'.")


if __name__ == "__main__":
    main()
