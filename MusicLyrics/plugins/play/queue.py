"""In-memory queue management for per-chat playback."""

from __future__ import annotations

import asyncio
import random
import logging
from dataclasses import dataclass, field
from typing import Optional

LOG = logging.getLogger(__name__)


@dataclass
class QueueItem:
    """Single item in the playback queue."""

    title: str
    url: str
    media_path: str  # local file path OR direct stream URL
    duration: int  # seconds
    requester: str  # user mention or name
    requester_id: int
    thumbnail: str = ""
    stream_type: str = "audio"  # "audio" or "video"
    platform: str = "youtube"
    is_stream_url: bool = False  # True if media_path is a URL

    # Backward compatibility alias
    @property
    def file_path(self) -> str:
        return self.media_path


@dataclass
class ChatQueue:
    """Queue state for a single chat."""

    items: list[QueueItem] = field(default_factory=list)
    loop_mode: bool = False
    current_index: int = 0

    @property
    def current(self) -> Optional[QueueItem]:
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return None

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0


# ── Global queue store ───────────────────────────────────────────────────────
_queues: dict[int, ChatQueue] = {}
_lock = asyncio.Lock()


async def get_chat_queue(chat_id: int) -> ChatQueue:
    """Return (or create) the queue for *chat_id*."""
    async with _lock:
        if chat_id not in _queues:
            _queues[chat_id] = ChatQueue()
        return _queues[chat_id]


async def add_to_queue(chat_id: int, item: QueueItem) -> int:
    """Append *item* and return its 1-based position in the queue."""
    async with _lock:
        if chat_id not in _queues:
            _queues[chat_id] = ChatQueue()
        cq = _queues[chat_id]
        cq.items.append(item)
        position = len(cq.items)
    LOG.info("Queue %s: added #%d — %s", chat_id, position, item.title)
    return position


async def get_queue(chat_id: int) -> list[QueueItem]:
    cq = await get_chat_queue(chat_id)
    return list(cq.items)


async def get_current(chat_id: int) -> Optional[QueueItem]:
    cq = await get_chat_queue(chat_id)
    return cq.current


async def skip_queue(chat_id: int, force: bool = False) -> Optional[QueueItem]:
    """Advance to the next track; return it or ``None`` if queue ends.

    If *force* is True, skip even when loop mode is on (user pressed Skip).
    Auto-next (stream-end) should call with force=False so loop replays.
    """
    async with _lock:
        cq = _queues.get(chat_id)
        if cq is None:
            return None
        if cq.loop_mode and not force:
            return cq.current  # replay same track

        # If force-skipping out of loop, disable loop so auto-next works normally
        if cq.loop_mode and force:
            cq.loop_mode = False

        cq.current_index += 1
        if cq.current_index >= len(cq.items):
            return None  # queue exhausted
        return cq.current


async def clear_queue(chat_id: int) -> None:
    async with _lock:
        _queues.pop(chat_id, None)
    LOG.info("Queue %s: cleared.", chat_id)


async def toggle_loop(chat_id: int) -> bool:
    """Toggle loop and return new state."""
    cq = await get_chat_queue(chat_id)
    cq.loop_mode = not cq.loop_mode
    return cq.loop_mode


async def shuffle_queue(chat_id: int) -> None:
    """Shuffle upcoming items (keep current track in place)."""
    cq = await get_chat_queue(chat_id)
    upcoming_start = cq.current_index + 1
    if upcoming_start < len(cq.items):
        upcoming = cq.items[upcoming_start:]
        random.shuffle(upcoming)
        cq.items[upcoming_start:] = upcoming
    LOG.info("Queue %s: shuffled %d upcoming tracks.", chat_id,
             max(0, len(cq.items) - upcoming_start))


def format_duration(seconds: int) -> str:
    """Human-readable mm:ss or hh:mm:ss string."""
    if seconds <= 0:
        return "Live"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
