"""URL and text extraction utilities for MusicLyrics bot."""

from __future__ import annotations

import re
from typing import Optional

from pyrogram.types import Message

_URL_RE = re.compile(
    r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
    re.IGNORECASE,
)

_TIME_RE = re.compile(
    r"(\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|"
    r"h|hr|hrs|hour|hours|d|day|days|w|week|weeks)$",
    re.IGNORECASE,
)

_TIME_MULTIPLIERS = {
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
    "w": 604800, "week": 604800, "weeks": 604800,
}


async def extract_user(message: Message) -> tuple[Optional[int], Optional[str]]:
    """Extract a target user from *message*.

    Resolution order:
    1. Replied-to message sender.
    2. Mentioned user (text mention entity).
    3. Username argument (``@username``).
    4. Numeric user-ID argument.

    Returns
    -------
    tuple[int | None, str | None]
        ``(user_id, display_name)`` or ``(None, None)`` when no user is found.
    """
    # 1. Reply
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        return user.id, user.first_name

    args = message.text.split()[1:] if message.text else []

    if not args:
        return None, None

    arg = args[0]

    # 2 & 3. Mention entities
    if message.entities:
        for entity in message.entities:
            if entity.type.value == "text_mention" and entity.user:
                return entity.user.id, entity.user.first_name
            if entity.type.value == "mention":
                username = message.text[entity.offset + 1 : entity.offset + entity.length]
                try:
                    user = await message.chat._client.get_users(username)
                    return user.id, user.first_name
                except Exception:
                    return None, None

    # 4. Numeric user ID
    if arg.isdigit():
        uid = int(arg)
        try:
            user = await message.chat._client.get_users(uid)
            return user.id, user.first_name
        except Exception:
            return uid, str(uid)

    return None, None


def extract_time(time_string: str) -> int | None:
    """Parse a human time string (e.g. ``1h``, ``30m``, ``2d``) to seconds.

    Returns ``None`` if the string cannot be parsed.
    """
    match = _TIME_RE.match(time_string.strip())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2).lower()
    return value * _TIME_MULTIPLIERS.get(unit, 0)


def is_url(text: str) -> bool:
    """Return ``True`` if *text* looks like a URL."""
    return bool(_URL_RE.fullmatch(text.strip()))


def extract_urls(text: str) -> list[str]:
    """Return all URLs found in *text*."""
    return _URL_RE.findall(text)
