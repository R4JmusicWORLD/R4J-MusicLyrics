"""Anti-raid plugin — detect and stop mass-join raids."""

from __future__ import annotations

import time
import logging
from collections import defaultdict

from pyrogram import filters, Client
from pyrogram.types import Message, ChatPermissions
from pyrogram.enums import ChatMemberStatus

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import admin_required

LOG = logging.getLogger(__name__)

# Per-chat settings
_raid_settings: dict[int, dict] = defaultdict(
    lambda: {
        "enabled": False,
        "threshold": 10,  # joins within window triggers raid mode
        "window": 60,     # seconds
        "action": "mute",  # mute, kick, ban
        "raid_active": False,
        "raid_start": 0,
        "lockdown_duration": 300,  # 5 minutes
    }
)

# Track join timestamps per chat
_join_timestamps: dict[int, list[float]] = defaultdict(list)
# Track users who joined during raid
_raid_joiners: dict[int, list[int]] = defaultdict(list)


@bot.on_message(filters.command("antiraid") & filters.group)
@admin_required
async def antiraid_cmd(client: Client, message: Message):
    """Configure anti-raid protection.

    Usage:
        /antiraid on|off
        /antiraid threshold <number>
        /antiraid action <mute|kick|ban>
        /antiraid status
    """
    chat_id = message.chat.id
    args = message.text.split(None)
    settings = _raid_settings[chat_id]

    if len(args) < 2:
        return await message.reply_text(
            "**Anti-Raid Usage / ব্যবহার:**\n\n"
            "▸ `/antiraid on` — চালু করো\n"
            "▸ `/antiraid off` — বন্ধ করো\n"
            "▸ `/antiraid threshold <N>` — কতজন জয়েন করলে raid (ডিফল্ট: 10)\n"
            "▸ `/antiraid action <mute|kick|ban>` — action সেট করো\n"
            "▸ `/antiraid status` — বর্তমান সেটিংস দেখো"
        )

    sub = args[1].lower()

    if sub == "on":
        settings["enabled"] = True
        await message.reply_text(
            "🛡️ Anti-raid চালু করা হয়েছে। / Anti-raid enabled.\n"
            f"Threshold: {settings['threshold']} joins in {settings['window']}s"
        )
    elif sub == "off":
        settings["enabled"] = False
        settings["raid_active"] = False
        await message.reply_text(
            "❌ Anti-raid বন্ধ করা হয়েছে। / Anti-raid disabled."
        )
    elif sub == "threshold" and len(args) >= 3:
        try:
            n = int(args[2])
            if n < 3 or n > 100:
                return await message.reply_text("❌ Threshold 3-100 এর মধ্যে হতে হবে।")
            settings["threshold"] = n
            await message.reply_text(f"✅ Raid threshold সেট করা হয়েছে: **{n}**")
        except ValueError:
            await message.reply_text("❌ সংখ্যা দাও। / Provide a number.")
    elif sub == "action" and len(args) >= 3:
        action = args[2].lower()
        if action not in ("mute", "kick", "ban"):
            return await message.reply_text("❌ সঠিক action: `mute`, `kick`, `ban`")
        settings["action"] = action
        await message.reply_text(f"✅ Raid action সেট করা হয়েছে: **{action}**")
    elif sub == "status":
        status = "চালু ✅" if settings["enabled"] else "বন্ধ ❌"
        raid = "🔴 ACTIVE" if settings["raid_active"] else "🟢 Normal"
        await message.reply_text(
            f"**Anti-Raid Status:**\n\n"
            f"▸ Status: {status}\n"
            f"▸ Raid mode: {raid}\n"
            f"▸ Threshold: {settings['threshold']} joins / {settings['window']}s\n"
            f"▸ Action: `{settings['action']}`\n"
            f"▸ Lockdown: {settings['lockdown_duration']}s"
        )
    else:
        await message.reply_text("❌ ভুল কমান্ড। `/antiraid` দেখো।")


@bot.on_message(filters.new_chat_members, group=5)
async def _raid_watcher(client: Client, message: Message):
    """Monitor new member joins for raid patterns."""
    chat_id = message.chat.id
    settings = _raid_settings[chat_id]

    if not settings["enabled"]:
        return

    now = time.time()

    # Clean old timestamps
    window = settings["window"]
    _join_timestamps[chat_id] = [
        ts for ts in _join_timestamps[chat_id] if now - ts < window
    ]

    # Record new joins
    new_members = message.new_chat_members or []
    for member in new_members:
        _join_timestamps[chat_id].append(now)
        if not member.is_bot:
            _raid_joiners[chat_id].append(member.id)

    # Check if threshold exceeded
    if len(_join_timestamps[chat_id]) >= settings["threshold"]:
        if not settings["raid_active"]:
            settings["raid_active"] = True
            settings["raid_start"] = now

            await client.send_message(
                chat_id,
                "🚨 **RAID DETECTED / রেইড শনাক্ত হয়েছে!** 🚨\n\n"
                f"⏱ {len(_join_timestamps[chat_id])} জন {window} সেকেন্ডে জয়েন করেছে!\n"
                f"🔒 Auto-lockdown চালু হচ্ছে...\n"
                f"Action: **{settings['action']}**"
            )

        # Take action on recent joiners
        action = settings["action"]
        for user_id in _raid_joiners[chat_id]:
            try:
                if action == "mute":
                    await client.restrict_chat_member(
                        chat_id, user_id,
                        ChatPermissions(can_send_messages=False),
                    )
                elif action == "kick":
                    await client.ban_chat_member(chat_id, user_id)
                    await client.unban_chat_member(chat_id, user_id)
                elif action == "ban":
                    await client.ban_chat_member(chat_id, user_id)
            except Exception as e:
                LOG.debug("Raid action failed for %s: %s", user_id, e)

        _raid_joiners[chat_id].clear()

    # Auto-deactivate raid mode after lockdown duration
    if settings["raid_active"]:
        if now - settings["raid_start"] > settings["lockdown_duration"]:
            settings["raid_active"] = False
            _join_timestamps[chat_id].clear()
            try:
                await client.send_message(
                    chat_id,
                    "✅ Raid mode স্বয়ংক্রিয়ভাবে বন্ধ হয়েছে। / Raid mode auto-deactivated."
                )
            except Exception:
                pass
