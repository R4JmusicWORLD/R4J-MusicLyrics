"""Warning system plugin for MusicLyrics bot."""

from __future__ import annotations

import logging

from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from pyrogram.enums import ChatMemberStatus

from MusicLyrics.bot import bot
from MusicLyrics.mongo.warns_db import (
    add_warn,
    get_warns,
    remove_warn,
    reset_warns,
    get_warn_settings,
    set_warn_limit,
)
from MusicLyrics.helpers.decorators import admin_required
from config import Config

LOG = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _resolve_target(client: Client, message: Message) -> int | None:
    """Return the target user_id from reply or argument."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id

    if len(message.command) >= 2:
        arg = message.command[1]
        # Handle @username
        if arg.startswith("@"):
            try:
                user = await client.get_users(arg)
                return user.id
            except Exception:
                return None
        # Handle user_id
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


# ── /warn <user> <reason> ──────────────────────────────────────────────────

@bot.on_message(filters.command("warn") & filters.group)
@admin_required
async def warn_cmd(client: Client, message: Message):
    target_id = await _resolve_target(client, message)
    if not target_id:
        await message.reply_text(
            "**Usage:** `/warn <user> [reason]`\n"
            "অথবা কারো মেসেজে রিপ্লাই করে `/warn [reason]` দাও।"
        )
        return

    # Don't warn admins / sudo
    if target_id in Config.SUDO_USERS or target_id == Config.OWNER_ID:
        await message.reply_text("❌ Sudo ইউজার বা মালিককে warn করা যাবে না!")
        return

    if await _is_target_admin(client, message.chat.id, target_id):
        await message.reply_text("❌ অ্যাডমিনকে warn করা যাবে না! / Cannot warn an admin!")
        return

    # Extract reason
    args = message.text.split(None, 2)
    if message.reply_to_message and len(args) >= 2:
        reason = args[1]
    elif len(args) >= 3:
        reason = args[2]
    else:
        reason = "No reason provided"

    chat_id = message.chat.id
    count = await add_warn(chat_id, target_id, reason)
    limit = await get_warn_settings(chat_id)

    try:
        user = await client.get_users(target_id)
        user_mention = user.mention
    except Exception:
        user_mention = f"`{target_id}`"

    if count >= limit:
        # Warn limit reached -- ban the user
        try:
            await client.ban_chat_member(chat_id, target_id)
            await reset_warns(chat_id, target_id)
            await message.reply_text(
                f"**Warn Limit Reached!**\n\n"
                f"ইউজার / User: {user_mention}\n"
                f"Warning: {count}/{limit}\n"
                f"কারণ / Reason: {reason}\n\n"
                f"ইউজার ব্যান হয়েছে! / User has been banned!"
            )
        except Exception as e:
            LOG.warning("Warn ban failed: %s", e)
            await message.reply_text(f"❌ ব্যান করা যায়নি: {e}")
    else:
        await message.reply_text(
            f"**Warning!**\n\n"
            f"ইউজার / User: {user_mention}\n"
            f"Warning: {count}/{limit}\n"
            f"কারণ / Reason: {reason}\n\n"
            f"{limit - count}টি warning বাকি আছে ব্যান হওয়ার আগে।\n"
            f"{limit - count} warning(s) remaining before ban."
        )


# ── /warns <user> ──────────────────────────────────────────────────────────

@bot.on_message(filters.command("warns") & filters.group)
@admin_required
async def warns_cmd(client: Client, message: Message):
    target_id = await _resolve_target(client, message)
    if not target_id:
        await message.reply_text(
            "**Usage:** `/warns <user>`\n"
            "অথবা কারো মেসেজে রিপ্লাই করে `/warns` দাও।"
        )
        return

    chat_id = message.chat.id
    doc = await get_warns(chat_id, target_id)
    limit = await get_warn_settings(chat_id)

    try:
        user = await client.get_users(target_id)
        user_mention = user.mention
    except Exception:
        user_mention = f"`{target_id}`"

    if not doc or doc.get("count", 0) == 0:
        await message.reply_text(
            f"{user_mention} এর কোনো warning নেই। / Has no warnings."
        )
        return

    count = doc["count"]
    reasons = doc.get("reasons", [])

    lines = [
        f"**Warnings for {user_mention}**\n",
        f"মোট / Total: {count}/{limit}\n",
    ]
    for i, r in enumerate(reasons, 1):
        lines.append(f"{i}. {r or 'No reason'}")

    await message.reply_text("\n".join(lines))


# ── /rmwarn <user> ──────────────────────────────────────────────────────────

@bot.on_message(filters.command("rmwarn") & filters.group)
@admin_required
async def rmwarn_cmd(client: Client, message: Message):
    target_id = await _resolve_target(client, message)
    if not target_id:
        await message.reply_text(
            "**Usage:** `/rmwarn <user>`\n"
            "অথবা কারো মেসেজে রিপ্লাই করে `/rmwarn` দাও।"
        )
        return

    remaining = await remove_warn(message.chat.id, target_id)

    try:
        user = await client.get_users(target_id)
        user_mention = user.mention
    except Exception:
        user_mention = f"`{target_id}`"

    await message.reply_text(
        f"**শেষ warning সরানো হয়েছে!** / Last warning removed!\n"
        f"ইউজার / User: {user_mention}\n"
        f"বাকি warning / Remaining: {remaining}"
    )


# ── /resetwarns <user> ─────────────────────────────────────────────────────

@bot.on_message(filters.command("resetwarns") & filters.group)
@admin_required
async def resetwarns_cmd(client: Client, message: Message):
    target_id = await _resolve_target(client, message)
    if not target_id:
        await message.reply_text(
            "**Usage:** `/resetwarns <user>`\n"
            "অথবা কারো মেসেজে রিপ্লাই করে `/resetwarns` দাও।"
        )
        return

    await reset_warns(message.chat.id, target_id)

    try:
        user = await client.get_users(target_id)
        user_mention = user.mention
    except Exception:
        user_mention = f"`{target_id}`"

    await message.reply_text(
        f"**সব warning রিসেট হয়েছে!** / All warnings reset!\n"
        f"ইউজার / User: {user_mention}"
    )


# ── /warnlimit <number> ────────────────────────────────────────────────────

@bot.on_message(filters.command("warnlimit") & filters.group)
@admin_required
async def warnlimit_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        limit = await get_warn_settings(message.chat.id)
        await message.reply_text(
            f"**বর্তমান Warn Limit:** {limit}\n"
            f"পরিবর্তন করতে / To change: `/warnlimit <number>`"
        )
        return

    try:
        new_limit = int(message.command[1])
        if new_limit < 1:
            raise ValueError
    except ValueError:
        await message.reply_text("❌ সঠিক সংখ্যা দিন (১ বা তার বেশি)। / Provide a valid number (1+).")
        return

    await set_warn_limit(message.chat.id, new_limit)
    await message.reply_text(
        f"**Warn Limit সেট হয়েছে:** {new_limit}\n"
        f"{new_limit}টি warning পেলে ইউজার ব্যান হবে।\n"
        f"Users will be banned after {new_limit} warnings."
    )
