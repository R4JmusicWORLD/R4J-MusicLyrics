"""Download utilities for MusicLyrics bot."""

from __future__ import annotations

import os
import uuid

import aiohttp
import aiofiles

from config import Config

_DOWNLOADS = Config.DOWNLOADS_DIR
os.makedirs(_DOWNLOADS, exist_ok=True)

_THUMB_DIR = os.path.join(_DOWNLOADS, "thumbnails")
os.makedirs(_THUMB_DIR, exist_ok=True)


async def download_file(url: str, path: str | None = None) -> str:
    """Download a file from *url* and save it to *path*.

    Parameters
    ----------
    url:
        Direct download URL.
    path:
        Destination file path.  When ``None`` a random name inside the
        downloads directory is used.

    Returns
    -------
    str
        Absolute path to the saved file.
    """
    if path is None:
        ext = url.rsplit(".", 1)[-1].split("?")[0][:5] or "bin"
        path = os.path.join(_DOWNLOADS, f"{uuid.uuid4().hex}.{ext}")

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            resp.raise_for_status()
            async with aiofiles.open(path, "wb") as fp:
                async for chunk in resp.content.iter_chunked(1024 * 64):
                    await fp.write(chunk)
    return os.path.abspath(path)


async def download_thumbnail(url: str) -> str:
    """Download an image thumbnail and return its file path."""
    path = os.path.join(_THUMB_DIR, f"{uuid.uuid4().hex}.jpg")
    return await download_file(url, path)


def cleanup(path: str) -> None:
    """Remove a file if it exists (call after use)."""
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
