"""Custom auto-reply filters plugin for MusicLyrics bot."""

from __future__ import annotations

import logging

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus

from MusicLyrics.bot import bot
from MusicLyrics.mongo.filters_db import (
    add_filter,
    get_filter,
    get_all_filters,
    delete_filter,
)
from MusicLyrics.helpers.decorators import admin_required

LOG = logging.getLogger(__name__)


# ── /filter <keyword> <reply> ──────────────────────────────────────────────

@bot.on_message(filters.command("filter") & filters.group)
@admin_required
async def add_filter_cmd(client: Client, message: Message):
    # Support: /filter keyword reply text
    # Support: /filter keyword (reply to a message)
    args = message.text.split(None, 2)

    if len(args) < 2:
        await message.reply_text(
            "**Usage:** `/filter <keyword> <reply text>`\n"
            "অথবা কোনো মেসেজে রিপ্লাই করে `/filter <keyword>` দাও।\n"
            "Or reply to a message with `/filter <keyword>`."
        )
        return

    keyword = args[1].lower().strip()

    # Check if replying to a message
    reply = message.reply_to_message
    if reply:
        if reply.text:
            response = reply.text
        elif reply.caption:
            response = reply.caption
        elif reply.sticker:
            response = f"[sticker:{reply.sticker.file_id}]"
        elif reply.photo:
            cap = reply.caption or ""
            response = f"[photo:{reply.photo.file_id}]{cap}"
        elif reply.document:
            cap = reply.caption or ""
            response = f"[document:{reply.document.file_id}]{cap}"
        elif reply.animation:
            cap = reply.caption or ""
            response = f"[animation:{reply.animation.file_id}]{cap}"
        else:
            response = "..."
    elif len(args) >= 3:
        response = args[2]
    else:
        await message.reply_text(
            "❌ রিপ্লাই টেক্সট দিতে হবে। / You need to provide a reply text.\n"
            "Usage: `/filter <keyword> <reply>`"
        )
        return

    await add_filter(message.chat.id, keyword, response)
    await message.reply_text(
        f"**Filter সেভ হয়েছে!** / Filter saved!\n"
        f"Keyword: `{keyword}`\n"
        f"যখনই কেউ '{keyword}' লিখবে, বট রিপ্লাই দেবে।"
    )


# ── /filters ────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("filters") & filters.group)
async def list_filters_cmd(client: Client, message: Message):
    all_filters = await get_all_filters(message.chat.id)
    if not all_filters:
        await message.reply_text(
            "এই চ্যাটে কোনো ফিল্টার নেই। / No filters in this chat.\n"
            "ফিল্টার যোগ করতে: `/filter <keyword> <reply>`"
        )
        return

    lines = ["**এই চ্যাটের ফিল্টার / Filters in this chat:**\n"]
    for i, f in enumerate(all_filters, 1):
        lines.append(f"{i}. `{f['keyword']}`")

    await message.reply_text("\n".join(lines))


# ── /rmfilter <keyword> ──────────────────────────────────────────────────────

@bot.on_message(filters.command(["rmfilter", "delfilter"]) & filters.group)
@admin_required
async def stop_filter_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("**Usage:** `/rmfilter <keyword>`")
        return

    keyword = message.command[1].lower().strip()
    existing = await get_filter(message.chat.id, keyword)
    if not existing:
        await message.reply_text(
            f"❌ `{keyword}` নামে কোনো ফিল্টার নেই। / No filter named `{keyword}`."
        )
        return

    await delete_filter(message.chat.id, keyword)
    await message.reply_text(
        f"**Filter মুছে ফেলা হয়েছে!** / Filter deleted!\n"
        f"Keyword: `{keyword}`"
    )


# ── Filter matching on messages ────────────────────────────────────────────

@bot.on_message(filters.group & filters.text & ~filters.command(["filter", "filters", "stop"]), group=10)
async def filter_responder(client: Client, message: Message):
    if not message.text:
        return

    chat_id = message.chat.id
    text_lower = message.text.lower()

    all_f = await get_all_filters(chat_id)
    if not all_f:
        return

    for f in all_f:
        keyword = f["keyword"]
        if keyword not in text_lower:
            continue

        response = f["response"]

        try:
            # Handle special media filters
            if response.startswith("[sticker:"):
                file_id = response[9:-1]
                await message.reply_sticker(file_id)
            elif response.startswith("[photo:"):
                rest = response[7:]
                closing = rest.index("]")
                file_id = rest[:closing]
                caption = rest[closing + 1:] or None
                await message.reply_photo(file_id, caption=caption)
            elif response.startswith("[document:"):
                rest = response[10:]
                closing = rest.index("]")
                file_id = rest[:closing]
                caption = rest[closing + 1:] or None
                await message.reply_document(file_id, caption=caption)
            elif response.startswith("[animation:"):
                rest = response[11:]
                closing = rest.index("]")
                file_id = rest[:closing]
                caption = rest[closing + 1:] or None
                await message.reply_animation(file_id, caption=caption)
            else:
                await message.reply_text(response)
        except Exception as e:
            LOG.warning("Filter response failed for '%s': %s", keyword, e)

        break  # Only respond to the first matching filter
