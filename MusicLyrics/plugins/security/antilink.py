"""Anti-link plugin — auto-delete messages containing URLs/invite links."""

from __future__ import annotations

import re
import logging
from collections import defaultdict

from pyrogram import filters, Client
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus, ChatType

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import admin_required, _is_sudo_user

LOG = logging.getLogger(__name__)

# Per-chat settings: chat_id -> {"enabled": bool, "action": str, "whitelist": set}
_antilink_settings: dict[int, dict] = defaultdict(
    lambda: {"enabled": False, "action": "delete", "whitelist": set()}
)

# URL / invite link patterns
_URL_PATTERN = re.compile(
    r"(https?://\S+|t\.me/\S+|telegram\.me/\S+|telegram\.dog/\S+)", re.IGNORECASE
)
_INVITE_PATTERN = re.compile(
    r"(t\.me/joinchat/\S+|t\.me/\+\S+|chat\.whatsapp\.com/\S+|discord\.gg/\S+)",
    re.IGNORECASE,
)

# Track violations for escalation
_violations: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))


async def _is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if a user is admin/owner in the chat."""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


@bot.on_message(filters.command("antilink") & filters.group)
@admin_required
async def antilink_cmd(client: Client, message: Message):
    """Toggle anti-link or configure it.

    Usage:
        /antilink on|off
        /antilink action <delete|warn|mute|kick|ban>
        /antilink whitelist add <domain>
        /antilink whitelist remove <domain>
        /antilink whitelist list
        /antilink status
    """
    chat_id = message.chat.id
    args = message.text.split(None)

    if len(args) < 2:
        return await message.reply_text(
            "**Anti-Link Usage / ব্যবহার:**\n\n"
            "▸ `/antilink on` — চালু করো\n"
            "▸ `/antilink off` — বন্ধ করো\n"
            "▸ `/antilink action <delete|warn|mute|kick|ban>`\n"
            "▸ `/antilink whitelist add <domain>`\n"
            "▸ `/antilink whitelist remove <domain>`\n"
            "▸ `/antilink whitelist list`\n"
            "▸ `/antilink status`"
        )

    sub = args[1].lower()
    settings = _antilink_settings[chat_id]

    if sub == "on":
        settings["enabled"] = True
        await message.reply_text(
            "✅ Anti-link চালু করা হয়েছে। / Anti-link enabled.\n"
            "লিংক পাঠালে মেসেজ ডিলিট করা হবে।"
        )
    elif sub == "off":
        settings["enabled"] = False
        await message.reply_text(
            "❌ Anti-link বন্ধ করা হয়েছে। / Anti-link disabled."
        )
    elif sub == "action" and len(args) >= 3:
        action = args[2].lower()
        if action not in ("delete", "warn", "mute", "kick", "ban"):
            return await message.reply_text(
                "❌ সঠিক action দাও: `delete`, `warn`, `mute`, `kick`, `ban`"
            )
        settings["action"] = action
        await message.reply_text(
            f"✅ Anti-link action সেট করা হয়েছে: **{action}**"
        )
    elif sub == "whitelist" and len(args) >= 3:
        wl_action = args[2].lower()
        if wl_action == "add" and len(args) >= 4:
            domain = args[3].lower()
            settings["whitelist"].add(domain)
            await message.reply_text(f"✅ `{domain}` whitelist-এ যোগ করা হয়েছে।")
        elif wl_action == "remove" and len(args) >= 4:
            domain = args[3].lower()
            settings["whitelist"].discard(domain)
            await message.reply_text(f"✅ `{domain}` whitelist থেকে সরানো হয়েছে।")
        elif wl_action == "list":
            wl = settings["whitelist"]
            if wl:
                text = "**Whitelisted Domains:**\n" + "\n".join(f"▸ `{d}`" for d in wl)
            else:
                text = "Whitelist খালি। / Whitelist is empty."
            await message.reply_text(text)
        else:
            await message.reply_text("Usage: `/antilink whitelist add|remove|list`")
    elif sub == "status":
        status = "চালু ✅" if settings["enabled"] else "বন্ধ ❌"
        action = settings["action"]
        wl = ", ".join(settings["whitelist"]) or "None"
        await message.reply_text(
            f"**Anti-Link Status:**\n\n"
            f"▸ Status: {status}\n"
            f"▸ Action: `{action}`\n"
            f"▸ Whitelist: {wl}"
        )
    else:
        await message.reply_text("❌ ভুল কমান্ড। `/antilink` দেখো সব অপশন।")


@bot.on_message(filters.group & ~filters.service, group=8)
async def _antilink_watcher(client: Client, message: Message):
    """Watch messages for links and take action."""
    if not message.from_user:
        return
    chat_id = message.chat.id
    settings = _antilink_settings[chat_id]

    if not settings["enabled"]:
        return

    user_id = message.from_user.id

    # Skip admins and sudo
    if await _is_sudo_user(user_id) or await _is_admin(client, chat_id, user_id):
        return

    text = message.text or message.caption or ""
    if not _URL_PATTERN.search(text) and not _INVITE_PATTERN.search(text):
        return

    # Check whitelist
    whitelist = settings["whitelist"]
    if whitelist:
        urls_found = _URL_PATTERN.findall(text)
        all_whitelisted = all(
            any(wl_domain in url.lower() for wl_domain in whitelist)
            for url in urls_found
        )
        if all_whitelisted:
            return

    action = settings["action"]
    mention = message.from_user.mention

    try:
        await message.delete()
    except Exception:
        pass

    if action == "delete":
        await client.send_message(
            chat_id,
            f"🔗 {mention}, লিংক পাঠানো নিষেধ! মেসেজ ডিলিট করা হয়েছে।\n"
            f"Links are not allowed here!",
        )
    elif action == "warn":
        _violations[chat_id][user_id] += 1
        count = _violations[chat_id][user_id]
        await client.send_message(
            chat_id,
            f"⚠️ {mention}, লিংক পাঠানো নিষেধ! Warning {count}/3\n"
            f"3 warnings-এ mute করা হবে।",
        )
        if count >= 3:
            try:
                from pyrogram.types import ChatPermissions
                await client.restrict_chat_member(
                    chat_id, user_id,
                    ChatPermissions(can_send_messages=False),
                )
                await client.send_message(
                    chat_id, f"🔇 {mention} muted (3 link warnings)."
                )
            except Exception:
                pass
            _violations[chat_id][user_id] = 0
    elif action == "mute":
        try:
            from pyrogram.types import ChatPermissions
            await client.restrict_chat_member(
                chat_id, user_id,
                ChatPermissions(can_send_messages=False),
            )
            await client.send_message(
                chat_id,
                f"🔇 {mention} muted হয়েছে লিংক পাঠানোর জন্য।\n"
                f"Muted for sending links.",
            )
        except Exception as e:
            LOG.warning("Antilink mute failed: %s", e)
    elif action == "kick":
        try:
            await client.ban_chat_member(chat_id, user_id)
            await client.unban_chat_member(chat_id, user_id)
            await client.send_message(
                chat_id, f"🦵 {mention} kicked হয়েছে লিংক পাঠানোর জন্য।"
            )
        except Exception as e:
            LOG.warning("Antilink kick failed: %s", e)
    elif action == "ban":
        try:
            await client.ban_chat_member(chat_id, user_id)
            await client.send_message(
                chat_id, f"🚫 {mention} banned হয়েছে লিংক পাঠানোর জন্য।"
            )
        except Exception as e:
            LOG.warning("Antilink ban failed: %s", e)
