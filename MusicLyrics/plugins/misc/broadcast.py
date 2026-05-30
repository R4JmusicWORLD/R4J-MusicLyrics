"""Broadcast plugin — send message to all users/chats (sudo only)."""

import asyncio

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import sudo_required
from MusicLyrics.mongo.users_db import get_all_users
from MusicLyrics.mongo.chats_db import get_all_chats


@bot.on_message(filters.command("broadcast"))
@sudo_required
async def broadcast_cmd(client, message: Message):
    """Broadcast a message to all users and chats."""
    # Determine what to broadcast
    if message.reply_to_message:
        broadcast_msg = message.reply_to_message
    else:
        args = message.text.split(None, 1)
        if len(args) < 2:
            return await message.reply_text(
                "❌ ব্যবহার / Usage:\n"
                "`/broadcast <message>`\n"
                "অথবা একটি মেসেজে রিপ্লাই দিয়ে `/broadcast`"
            )
        broadcast_msg = None
        broadcast_text = args[1].strip()

    status = await message.reply_text(
        "📡 ব্রডকাস্ট শুরু হচ্ছে... / Starting broadcast..."
    )

    users = await get_all_users()
    chats = await get_all_chats()

    sent = 0
    failed = 0
    total = len(users) + len(chats)

    # Broadcast to users
    for user in users:
        try:
            uid = user["user_id"]
            if broadcast_msg:
                await broadcast_msg.copy(uid)
            else:
                await client.send_message(uid, broadcast_text)
            sent += 1
        except Exception:
            failed += 1

        if (sent + failed) % 25 == 0:
            try:
                await status.edit_text(
                    f"📡 **Broadcasting...**\n\n"
                    f"✅ Sent: {sent}\n"
                    f"❌ Failed: {failed}\n"
                    f"📊 Progress: {sent + failed}/{total}"
                )
            except Exception:
                pass
            await asyncio.sleep(1)

    # Broadcast to chats
    for chat in chats:
        try:
            cid = chat["chat_id"]
            if broadcast_msg:
                await broadcast_msg.copy(cid)
            else:
                await client.send_message(cid, broadcast_text)
            sent += 1
        except Exception:
            failed += 1

        if (sent + failed) % 25 == 0:
            try:
                await status.edit_text(
                    f"📡 **Broadcasting...**\n\n"
                    f"✅ Sent: {sent}\n"
                    f"❌ Failed: {failed}\n"
                    f"📊 Progress: {sent + failed}/{total}"
                )
            except Exception:
                pass
            await asyncio.sleep(1)

    await status.edit_text(
        f"📡 **ব্রডকাস্ট সম্পন্ন! / Broadcast Complete!**\n\n"
        f"✅ Sent: `{sent}`\n"
        f"❌ Failed: `{failed}`\n"
        f"📊 Total: `{total}`"
    )
