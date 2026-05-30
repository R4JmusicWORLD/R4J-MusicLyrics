"""Tag-all plugin — mention every member of a group."""

import asyncio

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatType

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import admin_required

# chat_id -> True means an active tagall is running
_active_tagall: dict[int, bool] = {}


@bot.on_message(filters.command("tagall"))
@admin_required
async def tagall_cmd(client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text(
            "❌ এই কমান্ড শুধু গ্রুপে কাজ করবে। / Works in groups only."
        )

    chat_id = message.chat.id
    if chat_id in _active_tagall:
        return await message.reply_text(
            "⚠️ ইতোমধ্যে tagall চলছে। বাতিল করতে /cancel দাও।\n"
            "A tagall is already running. Use /cancel to stop."
        )

    custom_msg = message.text.split(None, 1)
    custom_msg = custom_msg[1] if len(custom_msg) > 1 else "📢 সবাইকে ডাকা হচ্ছে! / Calling everyone!"

    _active_tagall[chat_id] = True
    status = await message.reply_text("📢 ট্যাগ করা শুরু হচ্ছে... / Starting tagall...")

    batch: list[str] = []
    count = 0
    total = 0

    try:
        async for member in client.get_chat_members(chat_id):
            if chat_id not in _active_tagall:
                break
            if member.user.is_bot or member.user.is_deleted:
                continue

            mention = member.user.mention
            batch.append(mention)
            total += 1

            if len(batch) == 5:
                text = f"**{custom_msg}**\n\n" + " | ".join(batch)
                await client.send_message(chat_id, text)
                batch.clear()
                count += 5
                await asyncio.sleep(1.5)
    except Exception as e:
        await status.edit_text(f"❌ Error: `{e}`")
        _active_tagall.pop(chat_id, None)
        return

    # Send remaining batch
    if batch and chat_id in _active_tagall:
        text = f"**{custom_msg}**\n\n" + " | ".join(batch)
        await client.send_message(chat_id, text)

    _active_tagall.pop(chat_id, None)
    await status.edit_text(
        f"✅ ট্যাগ সম্পন্ন! মোট {total} জনকে মেনশন করা হয়েছে।\n"
        f"Tagall done! Mentioned {total} members."
    )


@bot.on_message(filters.command("cancel"))
@admin_required
async def cancel_tagall(_, message: Message):
    chat_id = message.chat.id
    if chat_id in _active_tagall:
        del _active_tagall[chat_id]
        await message.reply_text(
            "🛑 Tagall বাতিল করা হয়েছে। / Tagall cancelled."
        )
    else:
        await message.reply_text(
            "⚠️ কোনো tagall চলছে না। / No active tagall to cancel."
        )
