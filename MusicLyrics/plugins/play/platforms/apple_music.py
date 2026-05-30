"""Apple Music URL parsing — extract song name, then search YouTube."""

from __future__ import annotations

import logging
import re
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

LOG = logging.getLogger(__name__)


def is_apple_music_url(url: str) -> bool:
    return bool(re.match(r"https?://music\.apple\.com/", url))


async def get_apple_music_track(url: str) -> Optional[dict]:
    """Scrape song title + artist from an Apple Music URL.

    Returns ``{'title': ..., 'artist': ..., 'query': ...}`` or None.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")

        # <title>Song Name - Artist — Apple Music</title>
        title_tag = soup.find("title")
        if not title_tag:
            return None

        raw = title_tag.get_text(" ", strip=True)
        # Common formats:
        #   "Song Name by Artist on Apple Music"
        #   "Song Name - Artist — Apple Music"
        cleaned = re.sub(r"\s*(—|-)\s*Apple Music.*$", "", raw, flags=re.I)
        cleaned = re.sub(r"\s*on\s*Apple Music.*$", "", cleaned, flags=re.I)

        # Try "Song by Artist"
        m = re.match(r"^(.+?)\s+by\s+(.+)$", cleaned, re.I)
        if m:
            title, artist = m.group(1).strip(), m.group(2).strip()
        else:
            # Fallback: use the whole cleaned string
            title = cleaned.strip()
            artist = ""

        query = f"{title} {artist}".strip()
        return {"title": title, "artist": artist, "query": query}
    except Exception:
        LOG.exception("Apple Music parse failed: %s", url)
        return None
