"""Welcome & goodbye message plugin for MusicLyrics bot."""

from __future__ import annotations

import logging

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)

from MusicLyrics.bot import bot
from MusicLyrics.mongo.chats_db import get_chat, update_chat_settings
from MusicLyrics.helpers.decorators import admin_required
from config import Config

LOG = logging.getLogger(__name__)

DEFAULT_WELCOME = (
    "স্বাগতম {name}! **{chat}** গ্রুপে তোমাকে স্বাগত জানাই।\n"
    "Welcome {name} to **{chat}**!\n"
    "মোট সদস্য / Total members: {count}"
)

DEFAULT_GOODBYE = (
    "বিদায় {name}! **{chat}** থেকে চলে গেছে।\n"
    "Goodbye {name}! Left **{chat}**."
)


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _get_welcome_settings(chat_id: int) -> dict:
    doc = await get_chat(chat_id)
    if not doc:
        return {
            "welcome_on": True,
            "welcome_text": DEFAULT_WELCOME,
            "welcome_media": None,
            "goodbye_on": True,
            "goodbye_text": DEFAULT_GOODBYE,
        }
    return {
        "welcome_on": doc.get("welcome_on", True),
        "welcome_text": doc.get("welcome_text", DEFAULT_WELCOME),
        "welcome_media": doc.get("welcome_media", None),
        "goodbye_on": doc.get("goodbye_on", True),
        "goodbye_text": doc.get("goodbye_text", DEFAULT_GOODBYE),
    }


def _format_welcome(template: str, user, chat) -> str:
    name = user.first_name or "User"
    if user.last_name:
        name += f" {user.last_name}"
    mention = user.mention
    chat_title = chat.title or "this chat"

    try:
        count = chat.members_count or "N/A"
    except Exception:
        count = "N/A"

    return (
        template
        .replace("{name}", mention)
        .replace("{first}", user.first_name or "User")
        .replace("{last}", user.last_name or "")
        .replace("{chat}", chat_title)
        .replace("{count}", str(count))
        .replace("{username}", f"@{user.username}" if user.username else name)
        .replace("{id}", str(user.id))
    )


# ── Welcome handler ────────────────────────────────────────────────────────

@bot.on_message(filters.new_chat_members & filters.group, group=5)
async def welcome_handler(client: Client, message: Message):
    chat_id = message.chat.id
    settings = await _get_welcome_settings(chat_id)

    if not settings["welcome_on"]:
        return

    for member in message.new_chat_members:
        if member.is_bot:
            continue

        text = _format_welcome(settings["welcome_text"], member, message.chat)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "I'm not a bot / আমি বট না",
                callback_data=f"welcome_verify_{member.id}",
            )]
        ])

        media = settings.get("welcome_media")
        try:
            if media:
                await client.send_photo(
                    chat_id,
                    photo=media,
                    caption=text,
                    reply_markup=keyboard,
                )
            else:
                await client.send_message(
                    chat_id,
                    text,
                    reply_markup=keyboard,
                )
        except Exception as e:
            LOG.warning("Welcome send failed: %s", e)


# ── Welcome verify callback ────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^welcome_verify_"))
async def welcome_verify_cb(client: Client, callback: CallbackQuery):
    target_id = int(callback.data.split("_")[2])

    if callback.from_user.id != target_id:
        await callback.answer(
            "এটা তোমার বাটন না! / This is not your button!",
            show_alert=True,
        )
        return

    await callback.answer("ভেরিফাই সফল! স্বাগতম! / Verified! Welcome!")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


# ── Goodbye handler ─────────────────────────────────────────────────────────

@bot.on_message(filters.left_chat_member & filters.group, group=5)
async def goodbye_handler(client: Client, message: Message):
    chat_id = message.chat.id
    settings = await _get_welcome_settings(chat_id)

    if not settings["goodbye_on"]:
        return

    member = message.left_chat_member
    if member.is_bot:
        return

    text = _format_welcome(settings["goodbye_text"], member, message.chat)
    try:
        await client.send_message(chat_id, text)
    except Exception as e:
        LOG.warning("Goodbye send failed: %s", e)


# ── /setwelcome <text> ──────────────────────────────────────────────────────

@bot.on_message(filters.command("setwelcome") & filters.group)
@admin_required
async def set_welcome_cmd(client: Client, message: Message):
    # Check for media welcome (replied photo/animation)
    if message.reply_to_message and (
        message.reply_to_message.photo or message.reply_to_message.animation
    ):
        media = None
        if message.reply_to_message.photo:
            media = message.reply_to_message.photo.file_id
        elif message.reply_to_message.animation:
            media = message.reply_to_message.animation.file_id

        caption = message.reply_to_message.caption or DEFAULT_WELCOME
        text_part = message.text.split(None, 1)
        if len(text_part) > 1:
            caption = text_part[1]

        await update_chat_settings(message.chat.id, {
            "welcome_text": caption,
            "welcome_media": media,
        })
        await message.reply_text(
            "**Welcome মিডিয়া সহ সেট হয়েছে!** / Welcome with media set!\n\n"
            "**Placeholders:** `{name}`, `{chat}`, `{count}`, `{first}`, `{username}`, `{id}`"
        )
        return

    text = message.text.split(None, 1)
    if len(text) < 2:
        await message.reply_text(
            "**Usage:** `/setwelcome <text>`\n\n"
            "**Placeholders:**\n"
            "`{name}` — ইউজারের নাম / User's name\n"
            "`{chat}` — চ্যাটের নাম / Chat name\n"
            "`{count}` — মোট সদস্য / Member count\n"
            "`{first}` — প্রথম নাম / First name\n"
            "`{username}` — ইউজারনেম / Username\n"
            "`{id}` — ইউজার আইডি / User ID\n\n"
            "মিডিয়া ওয়েলকাম সেট করতে ছবি/গিফ রিপ্লাই করে কমান্ড দাও।"
        )
        return

    welcome_text = text[1]
    await update_chat_settings(message.chat.id, {
        "welcome_text": welcome_text,
        "welcome_media": None,
    })
    await message.reply_text(
        "**Welcome মেসেজ সেট হয়েছে!** / Welcome message set!"
    )


# ── /welcome on/off ─────────────────────────────────────────────────────────

@bot.on_message(filters.command("welcome") & filters.group)
@admin_required
async def welcome_toggle(client: Client, message: Message):
    if len(message.command) < 2:
        settings = await _get_welcome_settings(message.chat.id)
        state = "ON" if settings["welcome_on"] else "OFF"
        await message.reply_text(
            f"**Welcome:** {state}\n"
            f"ব্যবহার / Usage: `/welcome on` বা `/welcome off`"
        )
        return

    arg = message.command[1].lower()
    if arg in ("on", "enable", "yes"):
        await update_chat_settings(message.chat.id, {"welcome_on": True})
        await message.reply_text("**Welcome চালু করা হয়েছে!** / Welcome enabled!")
    elif arg in ("off", "disable", "no"):
        await update_chat_settings(message.chat.id, {"welcome_on": False})
        await message.reply_text("**Welcome বন্ধ করা হয়েছে।** / Welcome disabled.")
    else:
        await message.reply_text("Usage: `/welcome on` বা `/welcome off`")


# ── /resetwelcome ───────────────────────────────────────────────────────────

@bot.on_message(filters.command("resetwelcome") & filters.group)
@admin_required
async def reset_welcome_cmd(client: Client, message: Message):
    await update_chat_settings(message.chat.id, {
        "welcome_text": DEFAULT_WELCOME,
        "welcome_media": None,
    })
    await message.reply_text(
        "**Welcome মেসেজ রিসেট হয়েছে!** / Welcome message reset to default."
    )


# ── /setgoodbye <text> ──────────────────────────────────────────────────────

@bot.on_message(filters.command("setgoodbye") & filters.group)
@admin_required
async def set_goodbye_cmd(client: Client, message: Message):
    text = message.text.split(None, 1)
    if len(text) < 2:
        await message.reply_text(
            "**Usage:** `/setgoodbye <text>`\n\n"
            "**Placeholders:** `{name}`, `{chat}`, `{count}`, `{first}`, `{username}`, `{id}`"
        )
        return

    goodbye_text = text[1]
    await update_chat_settings(message.chat.id, {"goodbye_text": goodbye_text})
    await message.reply_text(
        "**Goodbye মেসেজ সেট হয়েছে!** / Goodbye message set!"
    )


# ── /goodbye on/off ─────────────────────────────────────────────────────────

@bot.on_message(filters.command("goodbye") & filters.group)
@admin_required
async def goodbye_toggle(client: Client, message: Message):
    if len(message.command) < 2:
        settings = await _get_welcome_settings(message.chat.id)
        state = "ON" if settings["goodbye_on"] else "OFF"
        await message.reply_text(
            f"**Goodbye:** {state}\n"
            f"ব্যবহার / Usage: `/goodbye on` বা `/goodbye off`"
        )
        return

    arg = message.command[1].lower()
    if arg in ("on", "enable", "yes"):
        await update_chat_settings(message.chat.id, {"goodbye_on": True})
        await message.reply_text("**Goodbye চালু করা হয়েছে!** / Goodbye enabled!")
    elif arg in ("off", "disable", "no"):
        await update_chat_settings(message.chat.id, {"goodbye_on": False})
        await message.reply_text("**Goodbye বন্ধ করা হয়েছে।** / Goodbye disabled.")
    else:
        await message.reply_text("Usage: `/goodbye on` বা `/goodbye off`")
