"""Admin commands -- promote, demote, adminlist."""

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter, ChatType
from pyrogram.errors import (
    ChatAdminRequired,
    UserAdminInvalid,
    RPCError,
)

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import admin_required
from MusicLyrics.utils.extractor import extract_user


@bot.on_message(filters.command("promote") & filters.group)
@admin_required
async def promote_user(client: Client, message: Message):
    """Promote a user to admin.  Usage: /promote <user> [title]"""
    user_id, name = await extract_user(message)
    if not user_id:
        await message.reply_text("Please reply to a user or provide a user ID/username to promote.")
        return

    # Optional custom title from remaining args
    args = message.text.split()
    title = " ".join(args[2:]) if len(args) > 2 else ""

    try:
        await client.promote_chat_member(
            chat_id=message.chat.id,
            user_id=user_id,
            privileges=None,  # default admin privileges
        )
        if title:
            try:
                await client.set_administrator_title(message.chat.id, user_id, title)
            except RPCError:
                pass

        text = f"Successfully promoted **{name}** as admin."
        if title:
            text += f"\nTitle: **{title}**"
        await message.reply_text(text)

    except ChatAdminRequired:
        await message.reply_text("I need admin privileges with 'Add Admins' permission to promote users.")
    except UserAdminInvalid:
        await message.reply_text("Cannot promote this user -- they may already be an admin or the chat creator.")
    except RPCError as e:
        await message.reply_text(f"Failed to promote: `{e}`")


@bot.on_message(filters.command("demote") & filters.group)
@admin_required
async def demote_user(client: Client, message: Message):
    """Demote an admin.  Usage: /demote <user>"""
    user_id, name = await extract_user(message)
    if not user_id:
        await message.reply_text("Please reply to a user or provide a user ID/username to demote.")
        return

    try:
        await client.promote_chat_member(
            chat_id=message.chat.id,
            user_id=user_id,
            privileges=None,
        )
        # Revoke all privileges by promoting with nothing, then restrict
        from pyrogram.types import ChatPrivileges

        await client.promote_chat_member(
            chat_id=message.chat.id,
            user_id=user_id,
            privileges=ChatPrivileges(),
        )
        await message.reply_text(f"Successfully demoted **{name}**.")
    except ChatAdminRequired:
        await message.reply_text("I need admin privileges with 'Add Admins' permission to demote users.")
    except UserAdminInvalid:
        await message.reply_text("Cannot demote this user -- they may be the chat creator or promoted by another admin.")
    except RPCError as e:
        await message.reply_text(f"Failed to demote: `{e}`")


@bot.on_message(filters.command("adminlist") & filters.group)
async def admin_list(client: Client, message: Message):
    """List all admins in the chat."""
    try:
        admins = []
        creator = None
        async for member in client.get_chat_members(
            message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS
        ):
            if member.status == ChatMemberStatus.OWNER:
                creator = member.user
            else:
                admins.append(member.user)
    except RPCError as e:
        await message.reply_text(f"Failed to fetch admin list: `{e}`")
        return

    text_parts = [f"**Admins in {message.chat.title}:**\n"]

    if creator:
        text_parts.append(f"**Creator:** {creator.mention}")

    if admins:
        text_parts.append("\n**Admins:**")
        for idx, user in enumerate(admins, 1):
            text_parts.append(f"  {idx}. {user.mention}")

    text_parts.append(f"\n**Total:** {len(admins) + (1 if creator else 0)}")

    await message.reply_text("\n".join(text_parts))
