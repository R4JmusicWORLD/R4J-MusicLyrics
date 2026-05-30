"""Mute system plugin for MusicLyrics bot."""

from __future__ import annotations

import re
import time
import logging

from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from pyrogram.enums import ChatMemberStatus

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import admin_required
from config import Config

LOG = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────────────────

_TIME_RE = re.compile(r"^(\d+)([mhdw]?)$", re.IGNORECASE)

_TIME_UNITS = {
    "m": 60,
    "h": 3600,
    "d": 86400,
    "w": 604800,
}


def _parse_duration(text: str) -> int | None:
    """Parse a duration string like '1h', '30m', '2d'. Returns seconds or None."""
    m = _TIME_RE.match(text.strip())
    if not m:
        return None
    amount = int(m.group(1))
    unit = m.group(2).lower() if m.group(2) else "m"
    return amount * _TIME_UNITS.get(unit, 60)


def _format_duration(seconds: int) -> str:
    if seconds >= 86400:
        return f"{seconds // 86400} day(s)"
    if seconds >= 3600:
        return f"{seconds // 3600} hour(s)"
    return f"{seconds // 60} minute(s)"


async def _resolve_target(client: Client, message: Message) -> int | None:
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id
    if len(message.command) >= 2:
        arg = message.command[1]
        if arg.startswith("@"):
            try:
                user = await client.get_users(arg)
                return user.id
            except Exception:
                return None
        try:
            return int(arg)
        except ValueError:
            return None
    return None


async def _is_target_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


# ── /mute <user> [time] ────────────────────────────────────────────────────

@bot.on_message(filters.command("mute") & filters.group)
@admin_required
async def mute_cmd(client: Client, message: Message):
    target_id = await _resolve_target(client, message)
    if not target_id:
        await message.reply_text(
            "**Usage:** `/mute <user> [time]`\n"
            "অথবা কারো মেসেজে রিপ্লাই করে `/mute [time]` দাও।\n"
            "সময় উদাহরণ / Time examples: `30m`, `1h`, `2d`"
        )
        return

    if target_id in Config.SUDO_USERS or target_id == Config.OWNER_ID:
        await message.reply_text("❌ Sudo ইউজার বা মালিককে mute করা যাবে না!")
        return

    if await _is_target_admin(client, message.chat.id, target_id):
        await message.reply_text("❌ অ্যাডমিনকে mute করা যাবে না! / Cannot mute an admin!")
        return

    # Check for optional time
    duration = None
    args = message.command
    time_arg = None
    if message.reply_to_message and len(args) >= 2:
        time_arg = args[1]
    elif len(args) >= 3:
        time_arg = args[2]

    until_date = 0
    duration_text = "চিরকাল / Permanently"
    if time_arg:
        seconds = _parse_duration(time_arg)
        if seconds:
            until_date = int(time.time()) + seconds
            duration_text = _format_duration(seconds)

    try:
        user = await client.get_users(target_id)
        user_mention = user.mention
    except Exception:
        user_mention = f"`{target_id}`"

    try:
        await client.restrict_chat_member(
            message.chat.id,
            target_id,
            ChatPermissions(),
            until_date=until_date if until_date else 0,
        )
        await message.reply_text(
            f"**Muted!**\n\n"
            f"ইউজার / User: {user_mention}\n"
            f"সময়কাল / Duration: {duration_text}\n"
            f"By: {message.from_user.mention}"
        )
    except Exception as e:
        LOG.warning("Mute failed: %s", e)
        await message.reply_text(f"❌ Mute করা যায়নি: {e}")


# ── /unmute <user> ──────────────────────────────────────────────────────────

@bot.on_message(filters.command("unmute") & filters.group)
@admin_required
async def unmute_cmd(client: Client, message: Message):
    target_id = await _resolve_target(client, message)
    if not target_id:
        await message.reply_text(
            "**Usage:** `/unmute <user>`\n"
            "অথবা কারো মেসেজে রিপ্লাই করে `/unmute` দাও।"
        )
        return

    try:
        user = await client.get_users(target_id)
        user_mention = user.mention
    except Exception:
        user_mention = f"`{target_id}`"

    try:
        await client.restrict_chat_member(
            message.chat.id,
            target_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await message.reply_text(
            f"**Unmuted!**\n\n"
            f"ইউজার / User: {user_mention}\n"
            f"By: {message.from_user.mention}"
        )
    except Exception as e:
        LOG.warning("Unmute failed: %s", e)
        await message.reply_text(f"❌ Unmute করা যায়নি: {e}")


# ── /tmute <user> <time> ───────────────────────────────────────────────────

@bot.on_message(filters.command("tmute") & filters.group)
@admin_required
async def tmute_cmd(client: Client, message: Message):
    target_id = await _resolve_target(client, message)
    if not target_id:
        await message.reply_text(
            "**Usage:** `/tmute <user> <time>`\n"
            "অথবা কারো মেসেজে রিপ্লাই করে `/tmute <time>` দাও।\n"
            "সময় উদাহরণ / Time examples: `30m`, `1h`, `2d`"
        )
        return

    if target_id in Config.SUDO_USERS or target_id == Config.OWNER_ID:
        await message.reply_text("❌ Sudo ইউজার বা মালিককে mute করা যাবে না!")
        return

    if await _is_target_admin(client, message.chat.id, target_id):
        await message.reply_text("❌ অ্যাডমিনকে mute করা যাবে না! / Cannot mute an admin!")
        return

    # Get time argument
    args = message.command
    time_arg = None
    if message.reply_to_message and len(args) >= 2:
        time_arg = args[1]
    elif len(args) >= 3:
        time_arg = args[2]

    if not time_arg:
        await message.reply_text(
            "❌ সময় উল্লেখ করো! / Specify a duration!\n"
            "Example: `/tmute @user 1h`"
        )
        return

    seconds = _parse_duration(time_arg)
    if not seconds:
        await message.reply_text(
            "❌ ভুল সময় ফরম্যাট! / Invalid time format!\n"
            "উদাহরণ / Examples: `30m`, `1h`, `2d`, `1w`"
        )
        return

    try:
        user = await client.get_users(target_id)
        user_mention = user.mention
    except Exception:
        user_mention = f"`{target_id}`"

    until_date = int(time.time()) + seconds
    try:
        await client.restrict_chat_member(
            message.chat.id,
            target_id,
            ChatPermissions(),
            until_date=until_date,
        )
        await message.reply_text(
            f"**Temporarily Muted!**\n\n"
            f"ইউজার / User: {user_mention}\n"
            f"সময়কাল / Duration: {_format_duration(seconds)}\n"
            f"By: {message.from_user.mention}"
        )
    except Exception as e:
        LOG.warning("TMute failed: %s", e)
        await message.reply_text(f"❌ Mute করা যায়নি: {e}")
