"""Comms: Discord bot messages and Gmail send. Both SENSITIVE tier — the approval
card shows the full recipient + complete message body before anything leaves.

Discord: bot token (own server only; user accounts are never automated).
Gmail: OAuth with narrow scope (gmail.send). Trusted code sends and verifies the
returned message id; the model only ever drafts.
"""

import base64
import logging
from email.mime.text import MIMEText

import httpx
import keyring

import config
from tools.registry import READ, SENSITIVE, tool

log = logging.getLogger("jarvis.comms")

DISCORD_API = "https://discord.com/api/v10"
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


# ---------- Discord ----------

def _discord_token() -> str | None:
    return keyring.get_password(config.KEYRING_SERVICE, "discord_bot_token")


async def _discord_get(path: str) -> list | dict:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{DISCORD_API}{path}", headers={"Authorization": f"Bot {_discord_token()}"}
        )
        r.raise_for_status()
        return r.json()


@tool(
    "discord_channels",
    "List servers and text channels the Jarvis Discord bot can post to.",
    {"type": "object", "properties": {}},
    READ,
)
async def discord_channels() -> dict:
    if not _discord_token():
        return {"error": "Discord not configured (store discord_bot_token)"}
    guilds = await _discord_get("/users/@me/guilds")
    out = []
    for g in guilds[:10]:
        chans = await _discord_get(f"/guilds/{g['id']}/channels")
        out.append(
            {
                "server": g["name"],
                "channels": [
                    {"id": c["id"], "name": c["name"]} for c in chans if c.get("type") == 0
                ],
            }
        )
    return {"servers": out}


@tool(
    "discord_send",
    "Send a message to a Discord channel via the Jarvis bot. Requires explicit "
    "user confirmation; the full text is shown before sending.",
    {
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "channel_name": {"type": "string", "description": "for the confirmation card"},
            "text": {"type": "string"},
        },
        "required": ["channel_id", "text"],
    },
    SENSITIVE,
    summary=lambda a: (
        "Send Discord message",
        f"#{a.get('channel_name') or a.get('channel_id')}",
        a.get("text", ""),
    ),
)
async def discord_send(channel_id: str, text: str, channel_name: str = "") -> dict:
    if not _discord_token():
        return {"error": "Discord not configured"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {_discord_token()}"},
            json={"content": text[:2000]},
        )
        r.raise_for_status()
        msg = r.json()
    return {"sent": True, "message_id": msg["id"], "channel_id": channel_id}


# ---------- Gmail ----------

def _gmail_creds():
    """Rebuild Credentials from the refresh token stored in Credential Manager."""
    import json

    from google.oauth2.credentials import Credentials

    raw = keyring.get_password(config.KEYRING_SERVICE, "gmail_oauth")
    if not raw:
        return None
    return Credentials.from_authorized_user_info(json.loads(raw), GMAIL_SCOPES)


def gmail_configured() -> bool:
    return _gmail_creds() is not None


@tool(
    "gmail_send",
    "Send an email from the user's Gmail. Requires explicit user confirmation; "
    "recipient, subject, and the complete body are shown before sending. "
    "Ask the user for any missing field — never guess a recipient.",
    {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "recipient email address"},
            "subject": {"type": "string"},
            "body": {"type": "string", "description": "plain-text body"},
        },
        "required": ["to", "subject", "body"],
    },
    SENSITIVE,
    summary=lambda a: (
        "Send email",
        a.get("to", "?"),
        f"Subject: {a.get('subject', '')}\n\n{a.get('body', '')}",
    ),
)
def gmail_send(to: str, subject: str, body: str) -> dict:
    creds = _gmail_creds()
    if creds is None:
        return {"error": "Gmail not configured (run scripts/setup_gmail.py)"}
    from googleapiclient.discovery import build

    service = build("gmail", "v1", credentials=creds)
    mime = MIMEText(body)
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    if not sent.get("id"):
        return {"error": "send failed: no message id returned"}
    return {"sent": True, "message_id": sent["id"], "to": to}
