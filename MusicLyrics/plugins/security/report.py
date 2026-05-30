"""Report system — users can report messages to admins."""

from __future__ import annotations

import logging

from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ChatMemberStatus

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import admin_required

LOG = logging.getLogger(__name__)

# Per-chat toggle
_report_enabled: dict[int, bool] = {}


@bot.on_message(filters.command("reports") & filters.group)
@admin_required
async def reports_toggle_cmd(client: Client, message: Message):
    """Toggle report system on/off.

    Usage:
        /reports on|off
        /reports — Show status
    """
    chat_id = message.chat.id
    args = message.text.split(None, 1)

    if len(args) < 2:
        enabled = _report_enabled.get(chat_id, True)
        status = "চালু ✅" if enabled else "বন্ধ ❌"
        return await message.reply_text(
            f"📢 **Report System:** {status}\n\n"
            f"ব্যবহার: `/reports on` বা `/reports off`"
        )

    sub = args[1].strip().lower()
    if sub == "on":
        _report_enabled[chat_id] = True
        await message.reply_text(
            "✅ Report system চালু করা হয়েছে। / Report system enabled.\n"
            "ইউজাররা `/report` দিয়ে অ্যাডমিনদের জানাতে পারবে।"
        )
    elif sub == "off":
        _report_enabled[chat_id] = False
        await message.reply_text(
            "❌ Report system বন্ধ করা হয়েছে। / Report system disabled."
        )
    else:
        await message.reply_text("❌ `/reports on` বা `/reports off` ব্যবহার করো।")


@bot.on_message(filters.command(["report", "admins"]) & filters.group)
async def report_cmd(client: Client, message: Message):
    """Report a message to group admins.

    Usage: Reply to a message with /report [reason]
    """
    chat_id = message.chat.id

    if not _report_enabled.get(chat_id, True):
        return

    if not message.reply_to_message:
        return await message.reply_text(
            "❌ যে মেসেজ রিপোর্ট করতে চাও সেটাতে রিপ্লাই দাও।\n"
            "Reply to the message you want to report."
        )

    reported_user = message.reply_to_message.from_user
    reporter = message.from_user

    if not reporter:
        return

    # Don't allow reporting admins
    if reported_user:
        try:
            member = await client.get_chat_member(chat_id, reported_user.id)
            if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                return await message.reply_text(
                    "❌ অ্যাডমিনদের রিপোর্ট করা যায় না। / Can't report admins."
                )
        except Exception:
            pass

    # Gather reason
    args = message.text.split(None, 1)
    reason = args[1].strip() if len(args) > 1 else "No reason given"

    # Notify admins
    reported_mention = reported_user.mention if reported_user else "Unknown"
    reporter_mention = reporter.mention

    # Build action buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔇 Mute", callback_data=f"rpt_mute_{reported_user.id if reported_user else 0}"),
            InlineKeyboardButton("🚫 Ban", callback_data=f"rpt_ban_{reported_user.id if reported_user else 0}"),
        ],
        [
            InlineKeyboardButton("🗑 Delete Msg", callback_data=f"rpt_del_{message.reply_to_message.id}"),
            InlineKeyboardButton("✅ Dismiss", callback_data="rpt_dismiss"),
        ],
    ])

    report_text = (
        f"🚨 **Report / রিপোর্ট** 🚨\n\n"
        f"▸ **Reported:** {reported_mention}\n"
        f"▸ **By:** {reporter_mention}\n"
        f"▸ **Reason:** {reason}\n"
        f"▸ **Chat:** {message.chat.title}"
    )

    # Tag admins
    admin_tags = []
    try:
        async for member in client.get_chat_members(chat_id, filter_="administrators"):
            if member.user and not member.user.is_bot:
                admin_tags.append(member.user.mention)
    except Exception:
        pass

    if admin_tags:
        report_text += "\n\n👑 " + " ".join(admin_tags[:10])

    await message.reply_text(report_text, reply_markup=keyboard)


@bot.on_callback_query(filters.regex(r"^rpt_"))
async def report_action_callback(client: Client, callback: CallbackQuery):
    """Handle report action buttons."""
    data = callback.data
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    # Only admins can take action
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await callback.answer("❌ Only admins can do this.", show_alert=True)
    except Exception:
        return await callback.answer("❌ Permission check failed.", show_alert=True)

    if data.startswith("rpt_mute_"):
        target_id = int(data.split("_")[2])
        if target_id:
            try:
                from pyrogram.types import ChatPermissions
                await client.restrict_chat_member(
                    chat_id, target_id,
                    ChatPermissions(can_send_messages=False),
                )
                await callback.message.edit_text(
                    callback.message.text + f"\n\n✅ Muted by {callback.from_user.mention}"
                )
            except Exception as e:
                await callback.answer(f"Failed: {e}", show_alert=True)
                return
    elif data.startswith("rpt_ban_"):
        target_id = int(data.split("_")[2])
        if target_id:
            try:
                await client.ban_chat_member(chat_id, target_id)
                await callback.message.edit_text(
                    callback.message.text + f"\n\n✅ Banned by {callback.from_user.mention}"
                )
            except Exception as e:
                await callback.answer(f"Failed: {e}", show_alert=True)
                return
    elif data.startswith("rpt_del_"):
        msg_id = int(data.split("_")[2])
        try:
            await client.delete_messages(chat_id, msg_id)
            await callback.answer("🗑 Message deleted.", show_alert=True)
        except Exception:
            await callback.answer("❌ Could not delete.", show_alert=True)
            return
    elif data == "rpt_dismiss":
        try:
            await callback.message.delete()
        except Exception:
            await callback.answer("Dismissed.", show_alert=True)
        return

    await callback.answer("✅ Done")
