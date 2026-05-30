"""User/chat info plugin for MusicLyrics bot."""

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatType

from MusicLyrics.bot import bot


@bot.on_message(filters.command("info"))
async def user_info_cmd(client, message: Message):
    """Show detailed user information."""
    target_user = None

    # From reply
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
    else:
        args = message.text.split(None, 1)
        if len(args) > 1:
            query = args[1].strip().lstrip("@")
            try:
                target_user = await client.get_users(query)
            except Exception:
                return await message.reply_text(
                    "❌ ইউজার খুঁজে পাওয়া যায়নি। / User not found."
                )
        elif message.from_user:
            target_user = message.from_user

    if not target_user:
        return await message.reply_text("❌ ইউজার নির্ধারণ করা যায়নি। / Could not determine user.")

    status = await message.reply_text("🔍 তথ্য খুঁজছি... / Fetching info...")

    # Profile photos count
    try:
        photos_count = await client.get_chat_photos_count(target_user.id)
    except Exception:
        photos_count = "N/A"

    # Common chats
    try:
        common = await client.get_common_chats(target_user.id)
        common_count = len(common)
    except Exception:
        common_count = "N/A"

    dc_id = target_user.dc_id or "N/A"
    username = f"@{target_user.username}" if target_user.username else "N/A"
    mention = target_user.mention

    text = (
        f"👤 **ইউজার তথ্য / User Info**\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"🏷️ **নাম / Name:** {target_user.first_name} {target_user.last_name or ''}\n"
        f"🆔 **ID:** `{target_user.id}`\n"
        f"📛 **Username:** {username}\n"
        f"🔗 **Mention:** {mention}\n"
        f"🌐 **DC ID:** {dc_id}\n"
        f"🤖 **Bot:** {'Yes' if target_user.is_bot else 'No'}\n"
        f"📸 **Profile Photos:** {photos_count}\n"
        f"👥 **Common Chats:** {common_count}\n"
        f"🔒 **Restricted:** {'Yes' if target_user.is_restricted else 'No'}\n"
        f"✅ **Verified:** {'Yes' if target_user.is_verified else 'No'}\n"
    )

    await status.edit_text(text)


@bot.on_message(filters.command("chatinfo"))
async def chat_info_cmd(client, message: Message):
    """Show detailed chat information."""
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text(
            "❌ এটি গ্রুপ/চ্যানেলে কাজ করবে। / Works in groups/channels only."
        )

    status = await message.reply_text("🔍 চ্যাট তথ্য খুঁজছি... / Fetching chat info...")

    try:
        chat = await client.get_chat(message.chat.id)
    except Exception as e:
        return await status.edit_text(f"❌ Error: `{e}`")

    members = getattr(chat, "members_count", "N/A")
    description = getattr(chat, "description", None) or "N/A"
    username = f"@{chat.username}" if chat.username else "N/A"
    chat_type = str(message.chat.type).split(".")[-1].title()

    text = (
        f"💬 **চ্যাট তথ্য / Chat Info**\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"🏷️ **Title:** {chat.title}\n"
        f"🆔 **ID:** `{chat.id}`\n"
        f"📛 **Username:** {username}\n"
        f"📊 **Type:** {chat_type}\n"
        f"👥 **Members:** {members}\n"
        f"📝 **Description:** {description[:200]}\n"
    )

    if hasattr(chat, "linked_chat") and chat.linked_chat:
        text += f"🔗 **Linked Chat:** {chat.linked_chat.title}\n"

    await status.edit_text(text)
