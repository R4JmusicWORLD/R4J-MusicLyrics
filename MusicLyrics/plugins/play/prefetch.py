"""Background prefetching of the *next* queue item.

When a track starts playing, this module kicks off a background task that
resolves the media for the NEXT item in the queue so it is ready to stream
the instant the current track ends or the user presses /skip.

The prefetch updates ``item.media_path`` and ``item.is_stream_url`` in place
inside the existing :class:`QueueItem`, so the player just needs to check
``item.media_path`` and use it directly — no extra plumbing.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from MusicLyrics.plugins.play.queue import get_chat_queue, QueueItem

LOG = logging.getLogger(__name__)

# One worker task per chat — cancelled & replaced whenever a new track starts.
_prefetch_tasks: dict[int, asyncio.Task] = {}


def _is_valid_media(media_path: str) -> bool:
    """Cheap validity check for a previously resolved media path."""
    if not media_path or not isinstance(media_path, str):
        return False
    mp = media_path.strip()
    if not mp:
        return False
    if mp.startswith(("http://", "https://")):
        # Trust stream URL — the streamer does a HEAD pre-check before play
        return True
    try:
        return os.path.isfile(mp) and os.path.getsize(mp) > 1024
    except Exception:
        return False


def is_prefetched(item: Optional[QueueItem]) -> bool:
    """Return True if *item* already has a usable media path."""
    if item is None:
        return False
    return _is_valid_media(item.media_path)


async def _resolve_item_media(item: QueueItem) -> bool:
    """Resolve media for *item* in the background — first success wins.

    Mutates ``item.media_path`` / ``item.is_stream_url`` on success.
    """
    # Imports kept local so a failure in one platform doesn't break import
    from MusicLyrics.plugins.play.platforms.youtube import (
        search_and_download_audio,
        search_and_download_video,
        get_audio_stream_url,
        get_video_stream_url,
        is_youtube_url,
    )
    from MusicLyrics.plugins.play.platforms.jiosaavn import (
        search_jiosaavn,
        search_and_download_jiosaavn,
    )
    from MusicLyrics.plugins.play.platforms.soundcloud import (
        search_and_download_soundcloud,
    )

    title = (item.title or "").strip()
    if not title:
        return False

    async def _try_youtube():
        try:
            if item.stream_type == "video":
                p, _ = await search_and_download_video(title)
            else:
                p, _ = await search_and_download_audio(title)
            if p and os.path.isfile(str(p)):
                return str(p), False
        except Exception:
            pass
        try:
            if is_youtube_url(item.url):
                if item.stream_type == "video":
                    u = await get_video_stream_url(item.url)
                else:
                    u = await get_audio_stream_url(item.url)
                if u:
                    return u, True
        except Exception:
            pass
        return None

    async def _try_jiosaavn():
        if item.stream_type == "video":
            return None  # JioSaavn is audio-only
        try:
            r = await search_jiosaavn(title)
            if r and r.get("download_url"):
                return r["download_url"], True
        except Exception:
            pass
        try:
            p, _ = await search_and_download_jiosaavn(title)
            if p and os.path.isfile(str(p)):
                return str(p), False
        except Exception:
            pass
        return None

    async def _try_soundcloud():
        try:
            p, info = await search_and_download_soundcloud(title)
            if p:
                if info and info.get("_is_stream_url"):
                    return str(p), True
                if os.path.isfile(str(p)):
                    return str(p), False
        except Exception:
            pass
        return None

    tasks = [
        asyncio.create_task(_try_youtube()),
        asyncio.create_task(_try_jiosaavn()),
        asyncio.create_task(_try_soundcloud()),
    ]
    pending = set(tasks)
    try:
        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for t in done:
                try:
                    result = t.result()
                except Exception:
                    result = None
                if result:
                    path, is_stream = result
                    for p in pending:
                        p.cancel()
                    item.media_path = path
                    item.is_stream_url = bool(is_stream)
                    return True
    finally:
        for p in pending:
            p.cancel()
    return False


async def prefetch_next(chat_id: int) -> None:
    """Kick off a background task to prefetch the NEXT item in *chat_id*'s queue.

    Safe to call repeatedly — cancels any previous prefetch for the chat first.
    Does nothing if the queue has fewer than 2 items or the next item already
    has a valid media path.
    """
    # Cancel any in-flight prefetch
    old = _prefetch_tasks.pop(chat_id, None)
    if old and not old.done():
        try:
            old.cancel()
        except Exception:
            pass

    async def _worker():
        try:
            cq = await get_chat_queue(chat_id)
            # Head is current; index 1 is the upcoming track
            if len(cq.items) < 2:
                return
            next_item = cq.items[1]
            if is_prefetched(next_item):
                LOG.info(
                    "Prefetch HIT for %s: '%s' already has valid media",
                    chat_id, next_item.title,
                )
                return
            LOG.info("Prefetch START for %s: '%s'", chat_id, next_item.title)
            ok = await _resolve_item_media(next_item)
            if ok:
                LOG.info(
                    "Prefetch DONE for %s: '%s' -> %s",
                    chat_id, next_item.title,
                    str(next_item.media_path)[:80],
                )
            else:
                LOG.warning(
                    "Prefetch MISS for %s: '%s' — will resolve at play time",
                    chat_id, next_item.title,
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            LOG.debug("Prefetch worker error for %s: %s", chat_id, e)

    task = asyncio.create_task(_worker())
    _prefetch_tasks[chat_id] = task


def cancel_prefetch(chat_id: int) -> None:
    """Cancel any pending prefetch task for *chat_id*."""
    t = _prefetch_tasks.pop(chat_id, None)
    if t and not t.done():
        try:
            t.cancel()
        except Exception:
            pass
