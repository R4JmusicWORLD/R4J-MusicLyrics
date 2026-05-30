"""Purge / delete commands for group admins."""

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import ChatAdminRequired, RPCError

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import admin_required

# Temporary storage for /purgefrom markers: {chat_id: message_id}
_purge_from: dict[int, int] = {}


@bot.on_message(filters.command("purge") & filters.group)
@admin_required
async def purge_messages(client: Client, message: Message):
    """Delete all messages from the replied message up to the current one."""
    if not message.reply_to_message:
        await message.reply_text("Reply to the first message you want to purge from.")
        return

    start_id = message.reply_to_message.id
    end_id = message.id
    chat_id = message.chat.id

    msg_ids = list(range(start_id, end_id + 1))

    try:
        # Pyrogram delete_messages accepts up to 100 at a time
        deleted = 0
        for i in range(0, len(msg_ids), 100):
            batch = msg_ids[i : i + 100]
            await client.delete_messages(chat_id, batch)
            deleted += len(batch)

        status = await message.reply_text(f"Purged **{deleted}** messages.")
        # Auto-delete the status after a few seconds
        import asyncio
        await asyncio.sleep(3)
        try:
            await status.delete()
        except Exception:
            pass
    except ChatAdminRequired:
        await message.reply_text("I need admin privileges with 'Delete Messages' permission.")
    except RPCError as e:
        await message.reply_text(f"Purge failed: `{e}`")


@bot.on_message(filters.command("purgefrom") & filters.group)
@admin_required
async def purge_from(client: Client, message: Message):
    """Mark the start of a purge range.  Reply to the first message."""
    if not message.reply_to_message:
        await message.reply_text("Reply to a message to mark the purge start point.")
        return

    _purge_from[message.chat.id] = message.reply_to_message.id
    await message.reply_text(
        f"Purge start set at message **{message.reply_to_message.id}**.\n"
        "Now reply to the last message and use /purgeto."
    )


@bot.on_message(filters.command("purgeto") & filters.group)
@admin_required
async def purge_to(client: Client, message: Message):
    """Mark the end of a purge range and execute the purge."""
    chat_id = message.chat.id
    start_id = _purge_from.pop(chat_id, None)

    if start_id is None:
        await message.reply_text("Use /purgefrom first to mark the start of the range.")
        return

    if not message.reply_to_message:
        await message.reply_text("Reply to the last message you want to purge.")
        return

    end_id = message.reply_to_message.id

    if end_id < start_id:
        start_id, end_id = end_id, start_id

    msg_ids = list(range(start_id, end_id + 1))
    # Also delete the command messages
    msg_ids.append(message.id)

    try:
        deleted = 0
        for i in range(0, len(msg_ids), 100):
            batch = msg_ids[i : i + 100]
            await client.delete_messages(chat_id, batch)
            deleted += len(batch)

        status = await client.send_message(chat_id, f"Purged **{deleted}** messages.")
        import asyncio
        await asyncio.sleep(3)
        try:
            await status.delete()
        except Exception:
            pass
    except ChatAdminRequired:
        await message.reply_text("I need admin privileges with 'Delete Messages' permission.")
    except RPCError as e:
        await message.reply_text(f"Purge failed: `{e}`")


@bot.on_message(filters.command("del") & filters.group)
@admin_required
async def delete_message(client: Client, message: Message):
    """Delete a single replied message."""
    if not message.reply_to_message:
        await message.reply_text("Reply to a message to delete it.")
        return

    try:
        await message.reply_to_message.delete()
        await message.delete()
    except ChatAdminRequired:
        await message.reply_text("I need admin privileges with 'Delete Messages' permission.")
    except RPCError as e:
        await message.reply_text(f"Delete failed: `{e}`")
