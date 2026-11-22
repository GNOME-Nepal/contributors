"""Edit a pinned Discord webhook message to show the top 10 GNOME Nepal contributors.

Required environment variables:
  DISCORD_WEBHOOK_URL  - the webhook URL (https://discord.com/api/webhooks/<id>/<token>)
  DISCORD_MESSAGE_ID   - id of a message previously sent by that webhook; it is edited in place

The message is edited rather than re-posted because contributors.json changes on
almost every scheduled run, and posting a new message each time would spam the channel.
"""

import json
import os
import sys

import requests

TOP_N = 10  # Discord allows at most 10 embeds per message
EMBED_COLOR = 0x4A90E2
MAX_TOTAL_CHARS = 6000  # Discord limit for all embed text in one message


def text(value, fallback="N/A", limit=1024):
    """Discord rejects null/empty embed values, so coerce and truncate."""
    value = (str(value).strip() if value is not None else "") or fallback
    return value if len(value) <= limit else value[: limit - 1] + "…"


def create_embed(rank, contributor):
    login = contributor["login"]
    return {
        "title": text(f"#{rank} {contributor.get('name') or login}", limit=256),
        "url": contributor["html_url"],
        "description": text(contributor.get("bio"), fallback="No bio provided", limit=300),
        "color": EMBED_COLOR,
        "thumbnail": {"url": contributor["avatar_url"]},
        "fields": [
            {"name": "GitHub", "value": text(login), "inline": True},
            {"name": "Contributions", "value": text(contributor.get("contributions", 0)), "inline": True},
        ],
    }


def embed_chars(embed):
    return (
        len(embed["title"])
        + len(embed["description"])
        + sum(len(f["name"]) + len(f["value"]) for f in embed["fields"])
    )


def main():
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    message_id = os.getenv("DISCORD_MESSAGE_ID")
    if not webhook_url or not message_id:
        sys.exit("DISCORD_WEBHOOK_URL and DISCORD_MESSAGE_ID must both be set")

    with open("contributors.json", "r", encoding="utf-8") as file:
        contributors = json.load(file)
    if not contributors:
        sys.exit("contributors.json is empty")

    top = sorted(contributors, key=lambda c: c.get("contributions", 0), reverse=True)[:TOP_N]
    embeds = [create_embed(rank, c) for rank, c in enumerate(top, start=1)]

    total = sum(embed_chars(e) for e in embeds)
    if total > MAX_TOTAL_CHARS:
        sys.exit(f"Embed text is {total} chars, over Discord's {MAX_TOTAL_CHARS} limit")

    payload = {
        "content": f"**Top {len(top)} GNOME Nepal contributors**",
        "embeds": embeds,
    }

    # Never fall back to POST on failure: that would post a new message every run.
    response = requests.patch(
        f"{webhook_url.rstrip('/')}/messages/{message_id}", json=payload, timeout=30
    )
    if response.status_code not in (200, 204):
        sys.exit(f"Failed to update Discord message: {response.status_code} {response.text}")
    print(f"Updated Discord message {message_id} with top {len(top)} contributors")


if __name__ == "__main__":
    main()
