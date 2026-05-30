"""Anti-flood plugin for MusicLyrics bot."""

from __future__ import annotations

import time
import logging
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import ChatAdminRequired, UserAdminInvalid

from MusicLyrics.bot import bot
from MusicLyrics.mongo.chats_db import get_chat, update_chat_settings
from MusicLyrics.helpers.decorators import admin_required
from config import Config

LOG = logging.getLogger(__name__)

# ── In-memory flood tracker ────────────────────────────────────────────────
# {chat_id: {user_id: [timestamp, ...]}}
_flood_log: dict[int, dict[int, list[float]]] = defaultdict(
    lambda: defaultdict(list)
)

# ── Settings cache ─────────────────────────────────────────────────────────
# {chat_id: (antiflood_on, flood_limit, flood_mode, cached_at)}
_settings_cache: dict[int, tuple[bool, int, str, float]] = {}
_SETTINGS_TTL = 60  # seconds

# ── Admin cache ────────────────────────────────────────────────────────────
# {(chat_id, user_id): (is_admin, cached_at)}
_admin_cache: dict[tuple[int, int], tuple[bool, float]] = {}
_ADMIN_TTL = 120  # seconds

DEFAULT_FLOOD_LIMIT = 10
FLOOD_WINDOW = 10  # seconds
MUTE_DURATION = 600  # 10 minutes


async def _get_flood_settings(chat_id: int) -> tuple[int, str]:
    """Return (flood_limit, flood_mode) for a chat (cached)."""
    now = time.time()
    cached = _settings_cache.get(chat_id)
    if cached and now - cached[3] < _SETTINGS_TTL:
        return cached[1], cached[2]
    try:
        doc = await get_chat(chat_id)
    except Exception:
        doc = None  # MongoDB down — use defaults
    if doc:
        limit = doc.get("flood_limit", DEFAULT_FLOOD_LIMIT)
        mode = doc.get("flood_mode", "mute")
        enabled = doc.get("antiflood", True)
    else:
        limit, mode, enabled = DEFAULT_FLOOD_LIMIT, "mute", True
    _settings_cache[chat_id] = (enabled, limit, mode, now)
    return limit, mode


async def _is_antiflood_on(chat_id: int) -> bool:
    now = time.time()
    cached = _settings_cache.get(chat_id)
    if cached and now - cached[3] < _SETTINGS_TTL:
        return cached[0]
    await _get_flood_settings(chat_id)  # populates cache
    cached = _settings_cache.get(chat_id)
    return cached[0] if cached else True


async def _is_admin_cached(client, chat_id: int, user_id: int) -> bool:
    """Check admin status with caching to avoid API spam."""
    now = time.time()
    key = (chat_id, user_id)
    cached = _admin_cache.get(key)
    if cached and now - cached[1] < _ADMIN_TTL:
        return cached[0]
    try:
        member = await client.get_chat_member(chat_id, user_id)
        is_admin = member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        is_admin = False
    _admin_cache[key] = (is_admin, now)
    return is_admin


def _is_flood(chat_id: int, user_id: int, limit: int) -> bool:
    now = time.time()
    history = _flood_log[chat_id][user_id]
    history[:] = [ts for ts in history if now - ts < FLOOD_WINDOW]
    history.append(now)
    return len(history) >= limit


# ── Flood detection handler ─────────────────────────────────────────────────

@bot.on_message(filters.group & ~filters.service, group=-4)
async def flood_watcher(client: Client, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    try:
        if not await _is_antiflood_on(chat_id):
            return
    except Exception:
        return  # MongoDB down — skip flood check, don't block

    # Skip admins / sudo
    if user_id in Config.SUDO_USERS or user_id == Config.OWNER_ID:
        return
    if await _is_admin_cached(client, chat_id, user_id):
        return

    limit, mode = await _get_flood_settings(chat_id)
    if not _is_flood(chat_id, user_id, limit):
        return

    # Clear flood log for this user
    _flood_log[chat_id].pop(user_id, None)

    try:
        if mode == "ban":
            await client.ban_chat_member(chat_id, user_id)
            action_text = "ব্যান / banned"
        elif mode == "kick":
            await client.ban_chat_member(chat_id, user_id)
            await client.unban_chat_member(chat_id, user_id)
            action_text = "কিক / kicked"
        else:  # mute
            until = int(time.time()) + MUTE_DURATION
            await client.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(),
                until_date=until,
            )
            action_text = f"মিউট / muted ({MUTE_DURATION // 60} min)"

        await client.send_message(
            chat_id,
            f"**Anti-Flood**\n"
            f"{message.from_user.mention} ফ্লাড করেছে এবং {action_text} হয়েছে।\n"
            f"Flooded and got {action_text}.\n"
            f"Limit: {limit} messages / {FLOOD_WINDOW}s",
        )
    except (ChatAdminRequired, UserAdminInvalid):
        LOG.debug("Antiflood action skipped in %s: bot is not admin.", chat_id)
    except Exception as e:
        LOG.warning("Antiflood action failed: %s", e)


# ── /setflood <number> ──────────────────────────────────────────────────────

@bot.on_message(filters.command("setflood") & filters.group)
@admin_required
async def set_flood_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "**Usage:** `/setflood <number>`\n"
            "উদাহরণ / Example: `/setflood 10`\n"
            "বন্ধ করতে / To disable: `/setflood off`"
        )
        return

    arg = message.command[1].lower()
    if arg in ("off", "no", "0"):
        await update_chat_settings(message.chat.id, {"antiflood": False})
        await message.reply_text(
            "**Anti-Flood বন্ধ করা হয়েছে।** / Anti-Flood disabled."
        )
        return

    try:
        limit = int(arg)
        if limit < 2:
            await message.reply_text("❌ সর্বনিম্ন ফ্লাড লিমিট ২। / Minimum flood limit is 2.")
            return
    except ValueError:
        await message.reply_text("❌ সঠিক সংখ্যা দিন। / Please provide a valid number.")
        return

    await update_chat_settings(
        message.chat.id,
        {"flood_limit": limit, "antiflood": True},
    )
    await message.reply_text(
        f"**Anti-Flood সেট হয়েছে!**\n"
        f"ফ্লাড লিমিট / Flood limit: **{limit}** messages per {FLOOD_WINDOW}s"
    )


# ── /flood ──────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("flood") & filters.group)
@admin_required
async def flood_info_cmd(client: Client, message: Message):
    enabled = await _is_antiflood_on(message.chat.id)
    limit, mode = await _get_flood_settings(message.chat.id)

    status = "ON" if enabled else "OFF"
    await message.reply_text(
        f"**Anti-Flood Settings**\n\n"
        f"স্ট্যাটাস / Status: **{status}**\n"
        f"লিমিট / Limit: **{limit}** messages per {FLOOD_WINDOW}s\n"
        f"অ্যাকশন / Action: **{mode}**\n\n"
        f"পরিবর্তন করতে / To change:\n"
        f"`/setflood <number>` — লিমিট সেট\n"
        f"`/setfloodmode <mute/ban/kick>` — অ্যাকশন সেট"
    )


# ── /setfloodmode <mute/ban/kick> ──────────────────────────────────────────

@bot.on_message(filters.command("setfloodmode") & filters.group)
@admin_required
async def set_flood_mode_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "**Usage:** `/setfloodmode <mute/ban/kick>`"
        )
        return

    mode = message.command[1].lower()
    if mode not in ("mute", "ban", "kick"):
        await message.reply_text(
            "❌ ভুল মোড! `mute`, `ban`, বা `kick` ব্যবহার করো।\n"
            "Invalid mode! Use `mute`, `ban`, or `kick`."
        )
        return

    await update_chat_settings(message.chat.id, {"flood_mode": mode})
    await message.reply_text(
        f"**Flood Mode সেট হয়েছে:** `{mode}`\n"
        f"ফ্লাডের ক্ষেত্রে ইউজার {mode} হবে।\n"
        f"Users will be {mode}d on flood."
    )
