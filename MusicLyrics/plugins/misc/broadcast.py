"""Broadcast plugin — send message to all users/chats (sudo only).

Supported flags (combine freely):
    -users      → only personal users
    -chats      → only groups/channels
    -pin        → pin the broadcast in target chats
    -pinloud    → pin with notification
    -forward    → forward instead of copy (shows original sender)
    -nobot      → do NOT remove dead/blocked users/chats from DB
    -dryrun     → simulate without sending

Usage:
    /broadcast <text>
    /broadcast -chats -pin <text>
    Reply to any message with /broadcast [-flags]
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Optional

from pyrogram import filters
from pyrogram.errors import (
    FloodWait,
    InputUserDeactivated,
    PeerIdInvalid,
    UserIsBlocked,
    ChatWriteForbidden,
    ChannelPrivate,
    ChatAdminRequired,
    RPCError,
)

# These error classes exist in newer pyrogram versions but not all.
# Import defensively so the plugin loads on either; missing names fall
# back to a unique sentinel class that will never match an isinstance
# check (so the except branch is effectively dead code on old versions).
def _opt_err(name: str):
    try:
        return getattr(__import__("pyrogram.errors", fromlist=[name]), name)
    except (ImportError, AttributeError):
        class _MissingErr(Exception):
            pass
        _MissingErr.__name__ = f"_Missing_{name}"
        return _MissingErr

SlowmodeWait      = _opt_err("SlowmodeWait")
UserDeactivated   = _opt_err("UserDeactivated")
ChannelInvalid    = _opt_err("ChannelInvalid")
ChatRestricted    = _opt_err("ChatRestricted")
MessageTooLong    = _opt_err("MessageTooLong")
MediaCaptionTooLong = _opt_err("MediaCaptionTooLong")

from pyrogram.types import Message

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import sudo_required
from MusicLyrics.mongo.users_db import get_all_users
from MusicLyrics.mongo.chats_db import get_all_chats

LOG = logging.getLogger(__name__)

# Try to import removal helpers; fall back to no-op if not present
try:
    from MusicLyrics.mongo.users_db import remove_user  # type: ignore
except ImportError:
    async def remove_user(_uid: int) -> None:  # type: ignore
        return None

try:
    from MusicLyrics.mongo.chats_db import remove_chat  # type: ignore
except ImportError:
    async def remove_chat(_cid: int) -> None:  # type: ignore
        return None


# ---------------- Tunables ----------------
# Parallel send workers.  Telegram's per-bot ceiling is ~30 msg/sec across
# different chats; 12 leaves headroom for the inevitable FloodWait without
# burning the whole quota on retries.
CONCURRENCY = 12
PROGRESS_EVERY = 3.0          # seconds between progress edits
MAX_FLOOD_WAIT = 90           # cap auto-sleep for FloodWait (s)
MAX_SLOWMODE_WAIT = 30        # cap auto-sleep for SlowmodeWait (s)
TRANSIENT_RETRIES = 2         # extra tries on network / RPC errors
TRANSIENT_BACKOFF_BASE = 1.5  # seconds — multiplied by attempt number
PER_SEND_TIMEOUT = 25.0       # per-target hard timeout (covers media uploads)
# ------------------------------------------

VALID_FLAGS = {
    "-users", "-chats", "-pin", "-pinloud",
    "-forward", "-nobot", "-dryrun",
}

# Errors that mean the target is GONE forever — safe to delete from DB.
DEAD_USER_ERRORS = (InputUserDeactivated, UserDeactivated, UserIsBlocked, PeerIdInvalid)
DEAD_CHAT_ERRORS = (
    ChatWriteForbidden,
    ChannelPrivate,
    ChannelInvalid,
    ChatRestricted,
    PeerIdInvalid,
)

# Errors that are "the bot can't post here right now" but the chat is still
# alive — keep it in the DB, just skip this broadcast.
SKIP_NO_REMOVE = (ChatAdminRequired, MessageTooLong, MediaCaptionTooLong)


def _parse_flags(text: str) -> tuple[set[str], str]:
    """Strip flags from message text. Returns (flags, remaining_text)."""
    parts = text.split()
    flags, rest = set(), []
    for p in parts[1:]:  # skip command itself
        if p in VALID_FLAGS:
            flags.add(p)
        else:
            rest.append(p)
    return flags, " ".join(rest).strip()


async def _send_one(
    client,
    target_id: int,
    target_kind: str,
    source_msg: Optional[Message],
    text: Optional[str],
    flags: set[str],
) -> tuple[bool, str]:
    """Send to one target.

    Returns ``(success, reason)`` where ``reason`` is one of:
        ""               → success
        "dead"           → target permanently gone, remove from DB
        "forbidden"      → bot lacks permission, keep in DB
        "too_long"       → message too long for this chat, keep in DB
        "transient"      → gave up after retries on a transient error
        "error:<name>"   → unexpected error
    """
    if "-dryrun" in flags:
        return True, ""

    is_user = target_kind == "user"
    dead_errors = DEAD_USER_ERRORS if is_user else DEAD_CHAT_ERRORS

    attempt = 0
    while True:
        attempt += 1
        try:
            async def _do_send():
                if source_msg is not None:
                    if "-forward" in flags:
                        return await source_msg.forward(target_id)
                    return await source_msg.copy(target_id)
                return await client.send_message(target_id, text)

            sent = await asyncio.wait_for(_do_send(), timeout=PER_SEND_TIMEOUT)

            if "-pin" in flags or "-pinloud" in flags:
                try:
                    await sent.pin(disable_notification=("-pin" in flags))
                except (ChatAdminRequired, ChatWriteForbidden, ChannelPrivate):
                    pass  # pin failure is non-fatal
                except Exception as pe:
                    LOG.debug("broadcast: pin failed for %s: %s", target_id, pe)

            return True, ""

        except FloodWait as e:
            wait = min(int(getattr(e, "value", 5)), MAX_FLOOD_WAIT)
            LOG.info("broadcast: FloodWait %ss for %s — sleeping", wait, target_id)
            await asyncio.sleep(wait + random.uniform(0.1, 0.5))
            # Retry as part of the same loop (no recursion → no stack growth)
            continue

        except SlowmodeWait as e:
            wait = min(int(getattr(e, "value", 5)), MAX_SLOWMODE_WAIT)
            LOG.info("broadcast: SlowmodeWait %ss for %s — sleeping", wait, target_id)
            await asyncio.sleep(wait + 0.3)
            continue

        except dead_errors as e:
            LOG.info("broadcast: dead target %s (%s) — will remove", target_id, type(e).__name__)
            return False, "dead"

        except SKIP_NO_REMOVE as e:
            LOG.info("broadcast: skip %s (%s)", target_id, type(e).__name__)
            reason = "too_long" if isinstance(e, (MessageTooLong, MediaCaptionTooLong)) else "forbidden"
            return False, reason

        except (asyncio.TimeoutError, RPCError, ConnectionError, OSError) as e:
            # Transient — retry up to TRANSIENT_RETRIES extra times
            if attempt <= TRANSIENT_RETRIES:
                backoff = TRANSIENT_BACKOFF_BASE * attempt + random.uniform(0, 0.5)
                LOG.warning(
                    "broadcast: transient %s for %s (attempt %d) — retry in %.1fs: %s",
                    type(e).__name__, target_id, attempt, backoff, e,
                )
                await asyncio.sleep(backoff)
                continue
            LOG.warning(
                "broadcast: transient %s for %s — giving up after %d attempts: %s",
                type(e).__name__, target_id, attempt, e,
            )
            return False, "transient"

        except Exception as e:
            LOG.warning(
                "broadcast: unexpected %s for %s: %s",
                type(e).__name__, target_id, e,
            )
            return False, f"error:{type(e).__name__}"


@bot.on_message(filters.command("broadcast"))
@sudo_required
async def broadcast_cmd(client, message: Message):
    """Broadcast a message to all users and/or chats."""
    flags, remaining = _parse_flags(message.text or "")

    # Determine payload
    source_msg: Optional[Message] = None
    text: Optional[str] = None
    if message.reply_to_message:
        source_msg = message.reply_to_message
    elif remaining:
        text = remaining
    else:
        return await message.reply_text(
            "❌ **ব্যবহার / Usage:**\n"
            "`/broadcast <message>` বা একটি মেসেজে রিপ্লাই দিয়ে `/broadcast`\n\n"
            "**Flags:**\n"
            "`-users` শুধু users\n"
            "`-chats` শুধু groups/channels\n"
            "`-pin` / `-pinloud` chats-এ pin করো\n"
            "`-forward` copy না করে forward করো\n"
            "`-nobot` dead users/chats delete করো না\n"
            "`-dryrun` test mode (পাঠাবে না)"
        )

    # Build target list (de-duplicated)
    targets: list[int] = []
    target_kind: list[str] = []  # parallel array: "user" | "chat"
    seen: set[int] = set()

    want_users = "-users" in flags or not ({"-users", "-chats"} & flags)
    want_chats = "-chats" in flags or not ({"-users", "-chats"} & flags)

    if want_users:
        try:
            users = await get_all_users()
        except Exception as e:
            LOG.exception("broadcast: get_all_users failed")
            return await message.reply_text(f"❌ users DB read failed: `{e}`")
        for u in users:
            uid = u.get("user_id") if isinstance(u, dict) else u
            if uid is None:
                continue
            try:
                uid_i = int(uid)
            except (TypeError, ValueError):
                continue
            if uid_i in seen:
                continue
            seen.add(uid_i)
            targets.append(uid_i)
            target_kind.append("user")

    if want_chats:
        try:
            chats = await get_all_chats()
        except Exception as e:
            LOG.exception("broadcast: get_all_chats failed")
            return await message.reply_text(f"❌ chats DB read failed: `{e}`")
        for c in chats:
            cid = c.get("chat_id") if isinstance(c, dict) else c
            if cid is None:
                continue
            try:
                cid_i = int(cid)
            except (TypeError, ValueError):
                continue
            if cid_i in seen:
                continue
            seen.add(cid_i)
            targets.append(cid_i)
            target_kind.append("chat")

    total = len(targets)
    if total == 0:
        return await message.reply_text("⚠️ কোনো target পাওয়া যায়নি / No targets found.")

    n_users = sum(1 for k in target_kind if k == "user")
    n_chats = total - n_users

    status = await message.reply_text(
        f"📡 **Broadcast শুরু হচ্ছে...**\n"
        f"🎯 Targets: `{total}` "
        f"(`{n_users}` users • `{n_chats}` chats)\n"
        f"⚙️ Mode: `{'forward' if '-forward' in flags else 'copy'}`"
        f"{' • pin' if ('-pin' in flags or '-pinloud' in flags) else ''}"
        f"{' • DRY RUN' if '-dryrun' in flags else ''}\n"
        f"🚀 Concurrency: `{CONCURRENCY}`"
    )

    # Counters
    sent = 0
    failed = 0
    removed = 0
    reasons: dict[str, int] = {}

    start = time.monotonic()
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    cleanup_dead = "-nobot" not in flags and "-dryrun" not in flags

    async def worker(idx: int):
        nonlocal sent, failed, removed
        async with sem:
            ok, reason = await _send_one(
                client, targets[idx], target_kind[idx], source_msg, text, flags
            )
            async with lock:
                if ok:
                    sent += 1
                else:
                    failed += 1
                    reasons[reason] = reasons.get(reason, 0) + 1
                    if reason == "dead" and cleanup_dead:
                        try:
                            if target_kind[idx] == "user":
                                await remove_user(targets[idx])
                            else:
                                await remove_chat(targets[idx])
                            removed += 1
                        except Exception as re:
                            LOG.debug("broadcast: remove %s failed: %s", targets[idx], re)

    def _summary_lines() -> str:
        if not reasons:
            return ""
        parts = []
        for k in ("dead", "forbidden", "too_long", "transient"):
            if reasons.get(k):
                parts.append(f"  • {k}: `{reasons[k]}`")
        for k, v in reasons.items():
            if k.startswith("error:"):
                parts.append(f"  • {k[6:]}: `{v}`")
        return "\n".join(parts)

    async def progress_loop():
        while True:
            await asyncio.sleep(PROGRESS_EVERY)
            done = sent + failed
            if done >= total:
                return
            now = time.monotonic()
            rate = done / max(now - start, 0.1)
            eta = (total - done) / max(rate, 0.1)
            extra = _summary_lines()
            body = (
                f"📡 **Broadcasting...**\n\n"
                f"✅ Sent: `{sent}`\n"
                f"❌ Failed: `{failed}`\n"
                f"🧹 Cleaned: `{removed}`\n"
                f"📊 Progress: `{done}/{total}` "
                f"({done * 100 // total}%)\n"
                f"⚡ Rate: `{rate:.1f}/s` • ETA `{int(eta)}s`"
            )
            if extra:
                body += f"\n\n**Failures:**\n{extra}"
            try:
                await status.edit_text(body)
            except FloodWait as e:
                await asyncio.sleep(int(getattr(e, "value", 2)))
            except Exception:
                pass

    progress_task = asyncio.create_task(progress_loop())
    try:
        # Fire all workers; semaphore limits concurrency.
        # return_exceptions=True so one worker crash never aborts the
        # whole broadcast — every chat gets its turn.
        await asyncio.gather(
            *(worker(i) for i in range(total)),
            return_exceptions=True,
        )
    finally:
        progress_task.cancel()
        try:
            await progress_task
        except (asyncio.CancelledError, Exception):
            pass

    elapsed = time.monotonic() - start
    final_extra = _summary_lines()
    final = (
        f"📡 **ব্রডকাস্ট সম্পন্ন! / Broadcast Complete!**\n\n"
        f"✅ Sent: `{sent}`\n"
        f"❌ Failed: `{failed}`\n"
        f"🧹 Cleaned: `{removed}`\n"
        f"📊 Total: `{total}` "
        f"(`{n_users}` users • `{n_chats}` chats)\n"
        f"⏱ Time: `{elapsed:.1f}s` "
        f"({sent / max(elapsed, 0.1):.1f}/s)"
    )
    if final_extra:
        final += f"\n\n**Failure breakdown:**\n{final_extra}"
    if "-dryrun" in flags:
        final += "\n\n⚠️ **DRY RUN — কিছু পাঠানো হয়নি।**"
    try:
        await status.edit_text(final)
    except Exception:
        LOG.exception("broadcast: failed to edit final status")
