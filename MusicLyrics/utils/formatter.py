"""Text formatting utilities for MusicLyrics bot."""

from __future__ import annotations

import html
import re


def format_duration(seconds: int | float) -> str:
    """Convert *seconds* to ``mm:ss`` or ``hh:mm:ss``."""
    seconds = int(seconds)
    if seconds < 0:
        seconds = 0
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def truncate(text: str, max_length: int = 100) -> str:
    """Truncate *text* to *max_length* characters, adding ellipsis if trimmed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "\u2026"


def format_number(n: int | float) -> str:
    """Format *n* with comma separators (e.g. ``1,234,567``)."""
    return f"{n:,}"


def escape_markdown(text: str) -> str:
    """Escape Telegram MarkdownV2 special characters."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special)}])", r"\\\1", text)


def mention_html(user_id: int, name: str) -> str:
    """Return an HTML ``<a>`` mention for *user_id*."""
    return f'<a href="tg://user?id={user_id}">{html.escape(name)}</a>'


def format_bytes(size: int | float) -> str:
    """Format *size* bytes into a human-readable string (KB / MB / GB / TB)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"
