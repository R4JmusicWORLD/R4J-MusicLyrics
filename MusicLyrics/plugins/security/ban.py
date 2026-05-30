"""Ban system plugin for MusicLyrics bot."""

from __future__ import annotations

import re
import time
import logging

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import ChatAdminRequired, UserAdminInvalid

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import admin_required
from config import Config

LOG = logging.getLogger(__name__)

_TIME_RE = re.compile(r"^(\d+)([mhdw]?)$", re.IGNORECASE)
_TIME_UNITS = {"m": 60, "h": 3600, "d": 86400, "w": 604800}


def _parse_duration(text: str) -> int | None:
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


# ── /ban <user> [reason] ───────────────────────────────────────────────────

@bot.on_message(filters.command("ban") & filters.group)
@admin_required
async def ban_cmd(client: Client, message: Message):
    target_id = await _resolve_target(client, message)
    if not target_id:
        await message.reply_text(
            "**Usage:** `/ban <user> [reason]`\n"
            "অথবা কারো মেসেজে রিপ্লাই করে `/ban [reason]` দাও।"
        )
        return

    if target_id in Config.SUDO_USERS or target_id == Config.OWNER_ID:
        await message.reply_text("❌ Sudo ইউজার বা মালিককে ban করা যাবে না!")
        return

    if await _is_target_admin(client, message.chat.id, target_id):
        await message.reply_text("❌ অ্যাডমিনকে ban করা যাবে না! / Cannot ban an admin!")
        return

    # Extract reason
    args = message.text.split(None, 2)
    if message.reply_to_message and len(args) >= 2:
        reason = args[1]
    elif len(args) >= 3:
        reason = args[2]
    else:
        reason = "No reason provided"

    try:
        user = await client.get_users(target_id)
        user_mention = user.mention
    except Exception:
        user_mention = f"`{target_id}`"

    try:
        await client.ban_chat_member(message.chat.id, target_id)
        await message.reply_text(
            f"**Banned!**\n\n"
            f"ইউজার / User: {user_mention}\n"
            f"কারণ / Reason: {reason}\n"
            f"By: {message.from_user.mention}"
        )
    except (ChatAdminRequired, UserAdminInvalid):
        await message.reply_text(
            "❌ Bot-এর admin অনুমতি নেই! / Bot doesn't have admin rights!\n"
            "Bot-কে admin বানিয়ে ban permission দিন।"
        )
    except Exception as e:
        LOG.warning("Ban failed: %s", e)
        await message.reply_text(f"❌ Ban করা যায়নি: {e}")


# ── /unban <user> ──────────────────────────────────────────────────────────

@bot.on_message(filters.command("unban") & filters.group)
@admin_required
async def unban_cmd(client: Client, message: Message):
    target_id = await _resolve_target(client, message)
    if not target_id:
        await message.reply_text(
            "**Usage:** `/unban <user>`\n"
            "অথবা কারো মেসেজে রিপ্লাই করে `/unban` দাও।"
        )
        return

    try:
        user = await client.get_users(target_id)
        user_mention = user.mention
    except Exception:
        user_mention = f"`{target_id}`"

    try:
        await client.unban_chat_member(message.chat.id, target_id)
        await message.reply_text(
            f"**Unbanned!**\n\n"
            f"ইউজার / User: {user_mention}\n"
            f"By: {message.from_user.mention}\n"
            f"ইউজার এখন আবার গ্রুপে যোগ দিতে পারবে।\n"
            f"User can now rejoin the group."
        )
    except (ChatAdminRequired, UserAdminInvalid):
        await message.reply_text(
            "❌ Bot-এর admin অনুমতি নেই! / Bot doesn't have admin rights!\n"
            "Bot-কে admin বানিয়ে ban permission দিন।"
        )
    except Exception as e:
        LOG.warning("Unban failed: %s", e)
        await message.reply_text(f"❌ Unban করা যায়নি: {e}")


# ── /tban <user> <time> [reason] ───────────────────────────────────────────

@bot.on_message(filters.command("tban") & filters.group)
@admin_required
async def tban_cmd(client: Client, message: Message):
    target_id = await _resolve_target(client, message)
    if not target_id:
        await message.reply_text(
            "**Usage:** `/tban <user> <time> [reason]`\n"
            "অথবা কারো মেসেজে রিপ্লাই করে `/tban <time> [reason]` দাও।\n"
            "সময় উদাহরণ / Time examples: `30m`, `1h`, `2d`"
        )
        return

    if target_id in Config.SUDO_USERS or target_id == Config.OWNER_ID:
        await message.reply_text("❌ Sudo ইউজার বা মালিককে ban করা যাবে না!")
        return

    if await _is_target_admin(client, message.chat.id, target_id):
        await message.reply_text("❌ অ্যাডমিনকে ban করা যাবে না! / Cannot ban an admin!")
        return

    # Parse time and reason
    args = message.command
    time_arg = None
    reason = "No reason provided"

    if message.reply_to_message:
        if len(args) >= 2:
            time_arg = args[1]
        if len(args) >= 3:
            reason = " ".join(args[2:])
    else:
        if len(args) >= 3:
            time_arg = args[2]
        if len(args) >= 4:
            reason = " ".join(args[3:])

    if not time_arg:
        await message.reply_text(
            "❌ সময় উল্লেখ করো! / Specify a duration!\n"
            "Example: `/tban @user 1h`"
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
        await client.ban_chat_member(
            message.chat.id, target_id, until_date=until_date
        )
        await message.reply_text(
            f"**Temporarily Banned!**\n\n"
            f"ইউজার / User: {user_mention}\n"
            f"সময়কাল / Duration: {_format_duration(seconds)}\n"
            f"কারণ / Reason: {reason}\n"
            f"By: {message.from_user.mention}"
        )
    except (ChatAdminRequired, UserAdminInvalid):
        await message.reply_text(
            "❌ Bot-এর admin অনুমতি নেই! / Bot doesn't have admin rights!\n"
            "Bot-কে admin বানিয়ে ban permission দিন।"
        )
    except Exception as e:
        LOG.warning("TBan failed: %s", e)
        await message.reply_text(f"❌ Ban করা যায়নি: {e}")


# ── /kick <user> [reason] ──────────────────────────────────────────────────

@bot.on_message(filters.command("kick") & filters.group)
@admin_required
async def kick_cmd(client: Client, message: Message):
    target_id = await _resolve_target(client, message)
    if not target_id:
        await message.reply_text(
            "**Usage:** `/kick <user> [reason]`\n"
            "অথবা কারো মেসেজে রিপ্লাই করে `/kick [reason]` দাও।"
        )
        return

    if target_id in Config.SUDO_USERS or target_id == Config.OWNER_ID:
        await message.reply_text("❌ Sudo ইউজার বা মালিককে kick করা যাবে না!")
        return

    if await _is_target_admin(client, message.chat.id, target_id):
        await message.reply_text("❌ অ্যাডমিনকে kick করা যাবে না! / Cannot kick an admin!")
        return

    # Extract reason
    args = message.text.split(None, 2)
    if message.reply_to_message and len(args) >= 2:
        reason = args[1]
    elif len(args) >= 3:
        reason = args[2]
    else:
        reason = "No reason provided"

    try:
        user = await client.get_users(target_id)
        user_mention = user.mention
    except Exception:
        user_mention = f"`{target_id}`"

    try:
        await client.ban_chat_member(message.chat.id, target_id)
        await client.unban_chat_member(message.chat.id, target_id)
        await message.reply_text(
            f"**Kicked!**\n\n"
            f"ইউজার / User: {user_mention}\n"
            f"কারণ / Reason: {reason}\n"
            f"By: {message.from_user.mention}\n\n"
            f"ইউজার আবার গ্রুপে যোগ দিতে পারবে।\n"
            f"User can rejoin the group."
        )
    except (ChatAdminRequired, UserAdminInvalid):
        await message.reply_text(
            "❌ Bot-এর admin অনুমতি নেই! / Bot doesn't have admin rights!\n"
            "Bot-কে admin বানিয়ে ban permission দিন।"
        )
    except Exception as e:
        LOG.warning("Kick failed: %s", e)
        await message.reply_text(f"❌ Kick করা যায়নি: {e}")
