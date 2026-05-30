"""Spotify URL parsing — extract track/playlist info, then search YouTube."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from config import Config

LOG = logging.getLogger(__name__)


def is_spotify_url(url: str) -> bool:
    return bool(re.match(r"https?://(open\.)?spotify\.com/", url))


def _spotify_type(url: str) -> Optional[str]:
    """Return 'track', 'playlist', 'album', or None."""
    m = re.search(r"spotify\.com/(track|playlist|album)/", url)
    return m.group(1) if m else None


def _get_client():
    """Create a spotipy client with client-credentials flow."""
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials

        cid = Config.SPOTIFY_CLIENT_ID
        csecret = Config.SPOTIFY_CLIENT_SECRET
        if not cid or not csecret:
            LOG.warning("Spotify credentials not configured.")
            return None
        return spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=cid, client_secret=csecret
            )
        )
    except Exception:
        LOG.exception("Failed to create Spotify client.")
        return None


async def get_spotify_track(url: str) -> Optional[dict]:
    """Return ``{'title': ..., 'artist': ..., 'duration': ..., 'query': ...}``."""
    sp = _get_client()
    if not sp:
        return _fallback_parse(url)
    try:
        loop = asyncio.get_running_loop()
        track = await loop.run_in_executor(None, sp.track, url)
        title = track["name"]
        artists = ", ".join(a["name"] for a in track["artists"])
        duration = track["duration_ms"] // 1000
        return {
            "title": title,
            "artist": artists,
            "duration": duration,
            "query": f"{title} {artists}",
            "thumbnail": (
                track["album"]["images"][0]["url"]
                if track.get("album", {}).get("images")
                else ""
            ),
        }
    except Exception:
        LOG.exception("Failed to fetch Spotify track: %s", url)
        return _fallback_parse(url)


async def get_spotify_playlist(url: str) -> list[dict]:
    """Return a list of track dicts from a Spotify playlist/album URL."""
    sp = _get_client()
    if not sp:
        return []
    try:
        stype = _spotify_type(url)
        tracks: list[dict] = []
        loop = asyncio.get_running_loop()

        if stype == "playlist":
            results = await loop.run_in_executor(None, sp.playlist_tracks, url)
            while results:
                for item in results["items"]:
                    t = item.get("track")
                    if not t:
                        continue
                    title = t["name"]
                    artists = ", ".join(a["name"] for a in t["artists"])
                    tracks.append({
                        "title": title,
                        "artist": artists,
                        "duration": t["duration_ms"] // 1000,
                        "query": f"{title} {artists}",
                    })
                results = await loop.run_in_executor(None, sp.next, results) if results.get("next") else None

        elif stype == "album":
            results = await loop.run_in_executor(None, sp.album_tracks, url)
            album = await loop.run_in_executor(None, sp.album, url)
            while results:
                for t in results["items"]:
                    title = t["name"]
                    artists = ", ".join(a["name"] for a in t["artists"])
                    tracks.append({
                        "title": title,
                        "artist": artists,
                        "duration": t["duration_ms"] // 1000,
                        "query": f"{title} {artists}",
                    })
                results = await loop.run_in_executor(None, sp.next, results) if results.get("next") else None

        return tracks
    except Exception:
        LOG.exception("Failed to fetch Spotify playlist: %s", url)
        return []


def _fallback_parse(url: str) -> Optional[dict]:
    """Try to extract a track name from the URL slug when API is unavailable."""
    m = re.search(r"spotify\.com/track/[A-Za-z0-9]+", url)
    if not m:
        return None
    return {"title": "Spotify Track", "artist": "", "duration": 0,
            "query": "Spotify Track"}
