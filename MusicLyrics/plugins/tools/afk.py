"""AFK (Away From Keyboard) plugin for MusicLyrics bot."""

import time

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot

# user_id -> {"reason": str, "time": float}
_afk_users: dict[int, dict] = {}


def _time_ago(seconds: float) -> str:
    """Return a human-readable duration string."""
    s = int(seconds)
    if s < 60:
        return f"{s} সেকেন্ড / seconds"
    m = s // 60
    if m < 60:
        return f"{m} মিনিট / minutes"
    h = m // 60
    return f"{h} ঘন্টা {m % 60} মিনিট / {h}h {m % 60}m"


@bot.on_message(filters.command("afk"))
async def afk_cmd(_, message: Message):
    """Set AFK status."""
    if not message.from_user:
        return

    user_id = message.from_user.id
    args = message.text.split(None, 1)
    reason = args[1].strip() if len(args) > 1 else "No reason"

    _afk_users[user_id] = {"reason": reason, "time": time.time()}

    await message.reply_text(
        f"💤 **{message.from_user.first_name}** এখন AFK।\n"
        f"{message.from_user.first_name} is now AFK.\n\n"
        f"📝 কারণ / Reason: {reason}"
    )


@bot.on_message(filters.group & ~filters.bot & ~filters.command("afk"), group=11)
async def afk_watcher(_, message: Message):
    """Watch for AFK-related activity in groups."""
    if not message.from_user:
        return

    user_id = message.from_user.id

    # If the user who sent a message is AFK, remove their AFK
    if user_id in _afk_users:
        afk_data = _afk_users.pop(user_id)
        duration = _time_ago(time.time() - afk_data["time"])
        await message.reply_text(
            f"👋 **{message.from_user.first_name}** ফিরে এসেছে!\n"
            f"{message.from_user.first_name} is back!\n\n"
            f"⏱ AFK ছিল: {duration}"
        )
        return

    # Check if the message mentions or replies to an AFK user
    if message.reply_to_message and message.reply_to_message.from_user:
        replied_id = message.reply_to_message.from_user.id
        if replied_id in _afk_users:
            afk_data = _afk_users[replied_id]
            duration = _time_ago(time.time() - afk_data["time"])
            name = message.reply_to_message.from_user.first_name
            await message.reply_text(
                f"💤 **{name}** এখন AFK আছে।\n"
                f"{name} is currently AFK.\n\n"
                f"📝 কারণ / Reason: {afk_data['reason']}\n"
                f"⏱ সময় / Since: {duration}"
            )
            return

    # Check mentions in entities
    if message.entities:
        for entity in message.entities:
            if entity.user and entity.user.id in _afk_users:
                afk_data = _afk_users[entity.user.id]
                duration = _time_ago(time.time() - afk_data["time"])
                await message.reply_text(
                    f"💤 **{entity.user.first_name}** এখন AFK আছে।\n"
                    f"{entity.user.first_name} is currently AFK.\n\n"
                    f"📝 কারণ / Reason: {afk_data['reason']}\n"
                    f"⏱ সময় / Since: {duration}"
                )
                break
