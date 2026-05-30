"""NSFW content detection plugin for MusicLyrics bot."""

from __future__ import annotations

import logging

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus

from MusicLyrics.bot import bot
from MusicLyrics.mongo.chats_db import get_chat, update_chat_settings
from MusicLyrics.helpers.decorators import admin_required
from config import Config

LOG = logging.getLogger(__name__)

# ── Basic NSFW keyword list (heuristic fallback) ───────────────────────────
_NSFW_KEYWORDS = [
    "porn", "xxx", "nsfw", "hentai", "nude", "naked",
    "sex video", "adult content", "onlyfans",
]


async def _is_nsfw_on(chat_id: int) -> bool:
    doc = await get_chat(chat_id)
    if doc:
        return doc.get("nsfw_check", False)
    return False


def _text_has_nsfw(text: str) -> bool:
    """Simple keyword-based NSFW check on text/captions."""
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in _NSFW_KEYWORDS)


async def _log_nsfw(client: Client, message: Message, reason: str):
    """Forward deleted NSFW content info to the log group."""
    if not Config.LOG_GROUP_ID:
        return
    try:
        user = message.from_user
        user_info = f"{user.mention} (`{user.id}`)" if user else "Unknown"
        await client.send_message(
            Config.LOG_GROUP_ID,
            f"**#NSFW_DELETED**\n"
            f"Chat: `{message.chat.title}` (`{message.chat.id}`)\n"
            f"User: {user_info}\n"
            f"Reason: {reason}\n"
            f"Message ID: `{message.id}`",
        )
    except Exception as e:
        LOG.warning("NSFW log failed: %s", e)


# ── NSFW watcher ────────────────────────────────────────────────────────────

@bot.on_message(filters.group & (filters.photo | filters.sticker | filters.animation | filters.video), group=-3)
async def nsfw_watcher(client: Client, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await _is_nsfw_on(chat_id):
        return

    # Skip admins / sudo
    if user_id in Config.SUDO_USERS or user_id == Config.OWNER_ID:
        return
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return
    except Exception:
        pass

    # Check caption / text for NSFW keywords
    caption = message.caption or ""
    if _text_has_nsfw(caption):
        try:
            await message.delete()
        except Exception:
            pass
        await client.send_message(
            chat_id,
            f"**NSFW Content Detected!**\n"
            f"{message.from_user.mention}, NSFW কন্টেন্ট পাঠানো নিষেধ।\n"
            f"NSFW content is not allowed. You have been warned.",
        )
        await _log_nsfw(client, message, "NSFW keyword in caption")
        return

    # Check file name if document/video
    file_name = ""
    if message.document:
        file_name = message.document.file_name or ""
    elif message.video:
        file_name = message.video.file_name or ""

    if _text_has_nsfw(file_name):
        try:
            await message.delete()
        except Exception:
            pass
        await client.send_message(
            chat_id,
            f"**NSFW Content Detected!**\n"
            f"{message.from_user.mention}, NSFW কন্টেন্ট পাঠানো নিষেধ।\n"
            f"NSFW content is not allowed. You have been warned.",
        )
        await _log_nsfw(client, message, "NSFW keyword in file name")


# Also check text messages for NSFW keyword links
@bot.on_message(filters.group & filters.text, group=-3)
async def nsfw_text_watcher(client: Client, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await _is_nsfw_on(chat_id):
        return

    if user_id in Config.SUDO_USERS or user_id == Config.OWNER_ID:
        return
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return
    except Exception:
        pass

    if _text_has_nsfw(message.text):
        try:
            await message.delete()
        except Exception:
            pass
        await client.send_message(
            chat_id,
            f"**NSFW Content Detected!**\n"
            f"{message.from_user.mention}, NSFW কন্টেন্ট পাঠানো নিষেধ।\n"
            f"NSFW content is not allowed.",
        )
        await _log_nsfw(client, message, "NSFW keyword in text")


# ── /nsfw on/off ────────────────────────────────────────────────────────────

@bot.on_message(filters.command("nsfw") & filters.group)
@admin_required
async def nsfw_toggle(client: Client, message: Message):
    if len(message.command) < 2:
        status = await _is_nsfw_on(message.chat.id)
        state = "ON" if status else "OFF"
        await message.reply_text(
            f"**NSFW Check:** {state}\n"
            f"ব্যবহার / Usage: `/nsfw on` বা `/nsfw off`"
        )
        return

    arg = message.command[1].lower()
    if arg in ("on", "enable", "yes"):
        await update_chat_settings(message.chat.id, {"nsfw_check": True})
        await message.reply_text(
            "**NSFW Check চালু করা হয়েছে!** / NSFW Check enabled!\n"
            "NSFW কন্টেন্ট অটোমেটিক ডিলিট হবে।"
        )
    elif arg in ("off", "disable", "no"):
        await update_chat_settings(message.chat.id, {"nsfw_check": False})
        await message.reply_text(
            "**NSFW Check বন্ধ করা হয়েছে।** / NSFW Check disabled."
        )
    else:
        await message.reply_text("Usage: `/nsfw on` বা `/nsfw off`")
