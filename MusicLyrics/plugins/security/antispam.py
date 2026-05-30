"""Anti-spam & global ban plugin for MusicLyrics bot."""

from __future__ import annotations

import time
import logging
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.errors import ChatAdminRequired, UserAdminInvalid

from MusicLyrics.bot import bot
from MusicLyrics.mongo.db import db
from MusicLyrics.mongo.chats_db import get_chat, update_chat_settings, get_all_chats
from MusicLyrics.helpers.decorators import admin_required, sudo_required
from config import Config

LOG = logging.getLogger(__name__)

_gban_col = db["gbans"]

# ── In-memory spam tracker ──────────────────────────────────────────────────
# {chat_id: {user_id: [(timestamp, msg_text), ...]}}
_msg_log: dict[int, dict[int, list[tuple[float, str]]]] = defaultdict(
    lambda: defaultdict(list)
)

SPAM_WINDOW = 10        # seconds
SPAM_MSG_LIMIT = 7      # max messages in window
SPAM_REPEAT_LIMIT = 4   # max identical messages in window
MUTE_DURATION = 300      # 5 minutes

# ── Admin cache ────────────────────────────────────────────────────────────
_admin_cache: dict[tuple[int, int], tuple[bool, float]] = {}
_ADMIN_TTL = 120  # seconds


async def _is_admin_cached(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is admin with caching to avoid rate limits."""
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


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _is_antispam_on(chat_id: int) -> bool:
    doc = await get_chat(chat_id)
    if doc:
        return doc.get("antispam", False)
    return False


async def _is_gbanned(user_id: int) -> bool:
    return await _gban_col.find_one({"user_id": user_id}) is not None


async def _get_gban(user_id: int):
    return await _gban_col.find_one({"user_id": user_id})


def _is_spam(chat_id: int, user_id: int, text: str) -> bool:
    now = time.time()
    history = _msg_log[chat_id][user_id]

    # Purge old entries
    history[:] = [(ts, t) for ts, t in history if now - ts < SPAM_WINDOW]
    history.append((now, text or ""))

    # Too many messages in window
    if len(history) >= SPAM_MSG_LIMIT:
        return True

    # Too many identical messages
    if text:
        repeats = sum(1 for _, t in history if t == text)
        if repeats >= SPAM_REPEAT_LIMIT:
            return True

    return False


# ── GBan enforcement on join / message ──────────────────────────────────────

@bot.on_message(filters.group, group=-10)
async def gban_watcher(client: Client, message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id

    try:
        gban = await _get_gban(user_id)
    except Exception:
        return  # MongoDB down — skip gban check, don't block
    if not gban:
        return

    try:
        await client.ban_chat_member(message.chat.id, user_id)
        await message.reply_text(
            f"**GBan Enforcement**\n"
            f"ইউজার `{user_id}` গ্লোবালি ব্যান করা আছে।\n"
            f"কারণ / Reason: {gban.get('reason', 'N/A')}"
        )
    except (ChatAdminRequired, UserAdminInvalid):
        LOG.debug("GBan enforce skipped in %s: bot is not admin.", message.chat.id)
    except Exception as e:
        LOG.warning("GBan enforce failed in %s: %s", message.chat.id, e)


# ── Spam detection handler ──────────────────────────────────────────────────

@bot.on_message(filters.group & ~filters.service, group=-5)
async def spam_watcher(client: Client, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    try:
        if not await _is_antispam_on(chat_id):
            return
    except Exception:
        return  # MongoDB down — skip spam check, don't block

    # Skip admins / sudo
    if user_id in Config.SUDO_USERS or user_id == Config.OWNER_ID:
        return
    if await _is_admin_cached(client, chat_id, user_id):
        return

    text = message.text or message.caption or ""
    if _is_spam(chat_id, user_id, text):
        # Delete spam messages
        try:
            await message.delete()
        except Exception:
            pass

        # Mute spammer temporarily
        try:
            until = int(time.time()) + MUTE_DURATION
            await client.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(),
                until_date=until,
            )
            _msg_log[chat_id].pop(user_id, None)
            await client.send_message(
                chat_id,
                f"**Anti-Spam**\n"
                f"{message.from_user.mention} স্প্যাম করার জন্য {MUTE_DURATION // 60} "
                f"মিনিটের জন্য মিউট হয়েছে।\n"
                f"Muted for {MUTE_DURATION // 60} minutes for spamming.",
            )
        except (ChatAdminRequired, UserAdminInvalid):
            LOG.debug("Antispam mute skipped in %s: bot is not admin.", chat_id)
        except Exception as e:
            LOG.warning("Antispam mute failed: %s", e)


# ── /antispam on/off ────────────────────────────────────────────────────────

@bot.on_message(filters.command("antispam") & filters.group)
@admin_required
async def antispam_toggle(client: Client, message: Message):
    if len(message.command) < 2:
        status = await _is_antispam_on(message.chat.id)
        state = "ON" if status else "OFF"
        await message.reply_text(
            f"**Anti-Spam:** {state}\n"
            f"ব্যবহার / Usage: `/antispam on` বা `/antispam off`"
        )
        return

    arg = message.command[1].lower()
    if arg in ("on", "enable", "yes"):
        await update_chat_settings(message.chat.id, {"antispam": True})
        await message.reply_text(
            "**Anti-Spam চালু করা হয়েছে!** / Anti-Spam enabled!\n"
            "স্প্যামকারীরা অটোমেটিক মিউট হবে।"
        )
    elif arg in ("off", "disable", "no"):
        await update_chat_settings(message.chat.id, {"antispam": False})
        await message.reply_text(
            "**Anti-Spam বন্ধ করা হয়েছে।** / Anti-Spam disabled."
        )
    else:
        await message.reply_text("Usage: `/antispam on` বা `/antispam off`")


# ── /gban ───────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("gban"))
@sudo_required
async def gban_cmd(client: Client, message: Message):
    args = message.text.split(None, 2)
    if len(args) < 2:
        await message.reply_text("**Usage:** `/gban <user_id> [reason]`")
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.reply_text("❌ সঠিক ইউজার আইডি দিন। / Provide a valid user ID.")
        return

    reason = args[2] if len(args) > 2 else "No reason provided"

    if target_id in Config.SUDO_USERS or target_id == Config.OWNER_ID:
        await message.reply_text("❌ Sudo ইউজার বা মালিককে gban করা যাবে না!")
        return

    await _gban_col.update_one(
        {"user_id": target_id},
        {"$set": {
            "user_id": target_id,
            "reason": reason,
            "banned_by": message.from_user.id,
            "date": int(time.time()),
        }},
        upsert=True,
    )

    status = await message.reply_text(
        f"**GBan Started**\n"
        f"ইউজার `{target_id}` কে সব চ্যাটে ব্যান করা হচ্ছে...\n"
        f"কারণ / Reason: {reason}"
    )

    success, failed = 0, 0
    chats = await get_all_chats()
    for chat_doc in chats:
        try:
            await client.ban_chat_member(chat_doc["chat_id"], target_id)
            success += 1
        except Exception:
            failed += 1

    await status.edit_text(
        f"**GBan Complete!**\n"
        f"ইউজার / User: `{target_id}`\n"
        f"কারণ / Reason: {reason}\n"
        f"সফল / Success: {success} চ্যাট\n"
        f"ব্যর্থ / Failed: {failed} চ্যাট"
    )

    if Config.LOG_GROUP_ID:
        try:
            await client.send_message(
                Config.LOG_GROUP_ID,
                f"**#GBAN**\n"
                f"User: `{target_id}`\n"
                f"By: {message.from_user.mention}\n"
                f"Reason: {reason}",
            )
        except Exception:
            pass


# ── /ungban ─────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("ungban"))
@sudo_required
async def ungban_cmd(client: Client, message: Message):
    args = message.text.split(None, 1)
    if len(args) < 2:
        await message.reply_text("**Usage:** `/ungban <user_id>`")
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.reply_text("❌ সঠিক ইউজার আইডি দিন। / Provide a valid user ID.")
        return

    result = await _gban_col.delete_one({"user_id": target_id})
    if result.deleted_count == 0:
        await message.reply_text(
            f"ইউজার `{target_id}` GBan তালিকায় নেই। / User is not gbanned."
        )
        return

    status = await message.reply_text(
        f"**UnGBan Started**\n"
        f"ইউজার `{target_id}` কে সব চ্যাটে আনব্যান করা হচ্ছে..."
    )

    success, failed = 0, 0
    chats = await get_all_chats()
    for chat_doc in chats:
        try:
            await client.unban_chat_member(chat_doc["chat_id"], target_id)
            success += 1
        except Exception:
            failed += 1

    await status.edit_text(
        f"**UnGBan Complete!**\n"
        f"ইউজার / User: `{target_id}`\n"
        f"সফল / Success: {success} চ্যাট\n"
        f"ব্যর্থ / Failed: {failed} চ্যাট"
    )

    if Config.LOG_GROUP_ID:
        try:
            await client.send_message(
                Config.LOG_GROUP_ID,
                f"**#UNGBAN**\n"
                f"User: `{target_id}`\n"
                f"By: {message.from_user.mention}",
            )
        except Exception:
            pass
