"""Auto-delete utility for bot messages.

Schedules messages for deletion after a configurable delay,
keeping group chats clean from service/status messages.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Union

LOG = logging.getLogger(__name__)

# Default delays (in seconds)
SERVICE_MSG_DELETE_DELAY = 20    # Error, usage, status messages
PLAYING_MSG_DELETE_DELAY = 120   # "Now Playing", queue messages (longer so they stay visible)
COMMAND_MSG_DELETE_DELAY = 5     # User's original /play, /vplay command


async def auto_delete(*messages, delay: int = SERVICE_MSG_DELETE_DELAY) -> None:
    """Schedule one or more messages for deletion after `delay` seconds.

    Silently ignores deletion failures (message already deleted,
    bot lacks delete permission, etc.).
    """
    if not messages:
        return

    async def _delete():
        await asyncio.sleep(delay)
        for msg in messages:
            if msg is None:
                continue
            try:
                await msg.delete()
            except Exception:
                # Message already deleted, no permission, etc.
                pass

    asyncio.create_task(_delete())


async def auto_delete_service(*messages) -> None:
    """Delete service/error/usage messages after short delay (15s)."""
    await auto_delete(*messages, delay=SERVICE_MSG_DELETE_DELAY)


async def auto_delete_playing(*messages) -> None:
    """Delete 'Now Playing'/queue messages after medium delay (30s)."""
    await auto_delete(*messages, delay=PLAYING_MSG_DELETE_DELAY)


async def auto_delete_cmd(*messages) -> None:
    """Delete user command messages (/play, /vplay) after short delay (5s)."""
    await auto_delete(*messages, delay=COMMAND_MSG_DELETE_DELAY)
