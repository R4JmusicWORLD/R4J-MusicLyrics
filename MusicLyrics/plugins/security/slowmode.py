"""Slow mode management plugin for admins."""

from __future__ import annotations

from pyrogram import filters, Client
from pyrogram.types import Message

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import admin_required


@bot.on_message(filters.command("slowmode") & filters.group)
@admin_required
async def slowmode_cmd(client: Client, message: Message):
    """Set or view slow mode for the chat.

    Usage:
        /slowmode <seconds>   — Set slow mode (0 to disable, max 86400)
        /slowmode off         — Disable slow mode
        /slowmode             — Show current setting
    """
    args = message.text.split(None, 1)

    if len(args) < 2:
        try:
            chat = await client.get_chat(message.chat.id)
            delay = getattr(chat, "slow_mode_delay", 0) or 0
            if delay:
                await message.reply_text(
                    f"🐢 **Slow Mode:** {delay} সেকেন্ড / seconds\n\n"
                    f"বন্ধ করতে: `/slowmode off`"
                )
            else:
                await message.reply_text(
                    "🐢 Slow mode বন্ধ আছে। / Slow mode is off.\n"
                    "চালু করতে: `/slowmode <seconds>`"
                )
        except Exception as e:
            await message.reply_text(f"❌ Error: `{e}`")
        return

    sub = args[1].strip().lower()

    if sub == "off":
        seconds = 0
    else:
        try:
            seconds = int(sub)
        except ValueError:
            return await message.reply_text(
                "❌ সংখ্যা দাও (সেকেন্ডে)। / Provide seconds.\n"
                "Example: `/slowmode 10`, `/slowmode off`"
            )

    if seconds < 0 or seconds > 86400:
        return await message.reply_text(
            "❌ 0 থেকে 86400 (24 ঘন্টা) এর মধ্যে হতে হবে।"
        )

    try:
        await client.set_slow_mode(message.chat.id, seconds)
        if seconds == 0:
            await message.reply_text(
                "✅ Slow mode বন্ধ করা হয়েছে। / Slow mode disabled."
            )
        else:
            await message.reply_text(
                f"✅ Slow mode সেট করা হয়েছে: **{seconds}** সেকেন্ড।\n"
                f"Slow mode set to **{seconds}** seconds."
            )
    except Exception as e:
        await message.reply_text(f"❌ Slow mode সেট করা যায়নি: `{e}`")
