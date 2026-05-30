"""Chat lock system plugin for MusicLyrics bot."""

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

# ── Supported lock types and their filter checks ──────────────────────────

LOCK_TYPES = {
    "sticker": "sticker",
    "gif": "animation",
    "animation": "animation",
    "url": "url",
    "link": "url",
    "forward": "forward",
    "photo": "photo",
    "video": "video",
    "document": "document",
    "audio": "audio",
    "voice": "voice",
    "contact": "contact",
    "location": "location",
    "game": "game",
    "poll": "poll",
    "dice": "dice",
    "text": "text",
}

# Canonical lock names (deduplicated)
CANONICAL_LOCKS = sorted(set(LOCK_TYPES.values()))


async def _get_locks(chat_id: int) -> dict:
    doc = await get_chat(chat_id)
    if doc:
        return doc.get("locks", {})
    return {}


def _check_message_type(message: Message) -> list[str]:
    """Return list of lock type keys that match this message."""
    types = []
    if message.sticker:
        types.append("sticker")
    if message.animation:
        types.append("animation")
    if message.photo:
        types.append("photo")
    if message.video:
        types.append("video")
    if message.document and not message.animation:
        types.append("document")
    if message.audio:
        types.append("audio")
    if message.voice:
        types.append("voice")
    if message.contact:
        types.append("contact")
    if message.location:
        types.append("location")
    if message.game:
        types.append("game")
    if message.poll:
        types.append("poll")
    if message.dice:
        types.append("dice")
    if message.forward_date:
        types.append("forward")

    # Check for URLs in text
    text = message.text or message.caption or ""
    if message.entities or message.caption_entities:
        from pyrogram.enums import MessageEntityType
        entities = (message.entities or []) + (message.caption_entities or [])
        for ent in entities:
            if ent.type in (MessageEntityType.URL, MessageEntityType.TEXT_LINK):
                types.append("url")
                break

    # Pure text message (no media)
    if message.text and not types:
        types.append("text")

    return types


# ── Lock enforcement handler ───────────────────────────────────────────────

@bot.on_message(filters.group & ~filters.service, group=-6)
async def lock_watcher(client: Client, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Skip admins / sudo
    if user_id in Config.SUDO_USERS or user_id == Config.OWNER_ID:
        return
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return
    except Exception:
        pass

    locks = await _get_locks(chat_id)
    if not locks:
        return

    msg_types = _check_message_type(message)
    for msg_type in msg_types:
        if locks.get(msg_type, False):
            try:
                await message.delete()
                # Avoid spamming -- only notify occasionally
                await client.send_message(
                    chat_id,
                    f"**Locked!**\n"
                    f"{message.from_user.mention}, `{msg_type}` এই চ্যাটে লক করা আছে।\n"
                    f"`{msg_type}` is locked in this chat.",
                )
            except Exception as e:
                LOG.warning("Lock delete failed: %s", e)
            break


# ── /lock <type> ────────────────────────────────────────────────────────────

@bot.on_message(filters.command("lock") & filters.group)
@admin_required
async def lock_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        types_list = ", ".join(f"`{t}`" for t in sorted(LOCK_TYPES.keys()))
        await message.reply_text(
            f"**Usage:** `/lock <type>`\n\n"
            f"**Available types:**\n{types_list}"
        )
        return

    lock_type = message.command[1].lower()
    if lock_type == "all":
        all_locks = {t: True for t in CANONICAL_LOCKS}
        await update_chat_settings(message.chat.id, {"locks": all_locks})
        await message.reply_text(
            "**সব টাইপ লক করা হয়েছে!** / All types locked!"
        )
        return

    if lock_type not in LOCK_TYPES:
        types_list = ", ".join(f"`{t}`" for t in sorted(LOCK_TYPES.keys()))
        await message.reply_text(
            f"❌ অজানা টাইপ! / Unknown type!\n\n"
            f"**Available types:**\n{types_list}\n\n"
            f"সব লক করতে: `/lock all`"
        )
        return

    canonical = LOCK_TYPES[lock_type]
    locks = await _get_locks(message.chat.id)
    locks[canonical] = True
    await update_chat_settings(message.chat.id, {"locks": locks})
    await message.reply_text(
        f"**`{canonical}` লক করা হয়েছে!** / `{canonical}` locked!\n"
        f"এই টাইপের মেসেজ অটোমেটিক ডিলিট হবে।"
    )


# ── /unlock <type> ──────────────────────────────────────────────────────────

@bot.on_message(filters.command("unlock") & filters.group)
@admin_required
async def unlock_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("**Usage:** `/unlock <type>` বা `/unlock all`")
        return

    lock_type = message.command[1].lower()
    if lock_type == "all":
        await update_chat_settings(message.chat.id, {"locks": {}})
        await message.reply_text(
            "**সব টাইপ আনলক করা হয়েছে!** / All types unlocked!"
        )
        return

    if lock_type not in LOCK_TYPES:
        await message.reply_text(
            f"❌ অজানা টাইপ! / Unknown type! "
            f"সব আনলক করতে: `/unlock all`"
        )
        return

    canonical = LOCK_TYPES[lock_type]
    locks = await _get_locks(message.chat.id)
    locks.pop(canonical, None)
    await update_chat_settings(message.chat.id, {"locks": locks})
    await message.reply_text(
        f"**`{canonical}` আনলক করা হয়েছে!** / `{canonical}` unlocked!"
    )


# ── /locks ──────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("locks") & filters.group)
@admin_required
async def locks_info_cmd(client: Client, message: Message):
    locks = await _get_locks(message.chat.id)

    lines = ["**Lock Settings / লক সেটিংস:**\n"]
    for lock_type in CANONICAL_LOCKS:
        status = "LOCKED" if locks.get(lock_type, False) else "unlocked"
        icon = "🔒" if locks.get(lock_type, False) else "🔓"
        lines.append(f"{icon} `{lock_type}`: {status}")

    await message.reply_text("\n".join(lines))
