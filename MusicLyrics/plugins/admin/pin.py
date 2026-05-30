"""Pin / unpin commands for group admins."""

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import ChatAdminRequired, RPCError

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import admin_required


@bot.on_message(filters.command("pin") & filters.group)
@admin_required
async def pin_message(client: Client, message: Message):
    """Pin the replied message."""
    if not message.reply_to_message:
        await message.reply_text("Reply to a message to pin it.")
        return

    try:
        await client.pin_chat_message(
            chat_id=message.chat.id,
            message_id=message.reply_to_message.id,
        )
        await message.reply_text("Message pinned successfully.")
    except ChatAdminRequired:
        await message.reply_text("I need admin privileges with 'Pin Messages' permission.")
    except RPCError as e:
        await message.reply_text(f"Failed to pin: `{e}`")


@bot.on_message(filters.command("unpin") & filters.group)
@admin_required
async def unpin_message(client: Client, message: Message):
    """Unpin the replied message, or the most recent pinned message."""
    msg_id = message.reply_to_message.id if message.reply_to_message else 0

    try:
        await client.unpin_chat_message(
            chat_id=message.chat.id,
            message_id=msg_id,
        )
        await message.reply_text("Message unpinned successfully.")
    except ChatAdminRequired:
        await message.reply_text("I need admin privileges with 'Pin Messages' permission.")
    except RPCError as e:
        await message.reply_text(f"Failed to unpin: `{e}`")


@bot.on_message(filters.command("unpinall") & filters.group)
@admin_required
async def unpin_all_messages(client: Client, message: Message):
    """Unpin all pinned messages in the chat."""
    try:
        await client.unpin_all_chat_messages(chat_id=message.chat.id)
        await message.reply_text("All pinned messages have been unpinned.")
    except ChatAdminRequired:
        await message.reply_text("I need admin privileges with 'Pin Messages' permission.")
    except RPCError as e:
        await message.reply_text(f"Failed to unpin all: `{e}`")


@bot.on_message(filters.command("pinned") & filters.group)
async def get_pinned(client: Client, message: Message):
    """Get a link to the last pinned message."""
    try:
        chat = await client.get_chat(message.chat.id)
        pinned = chat.pinned_message
        if not pinned:
            await message.reply_text("No pinned message in this chat.")
            return

        link = pinned.link
        if link:
            await message.reply_text(
                f"**Pinned message:** [Click here]({link})",
                disable_web_page_preview=True,
            )
        else:
            await message.reply_text(
                f"**Pinned message (ID {pinned.id}):**\n{pinned.text or '(media)'}"
            )
    except RPCError as e:
        await message.reply_text(f"Failed to fetch pinned message: `{e}`")
