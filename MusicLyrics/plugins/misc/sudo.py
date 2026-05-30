"""Sudo management plugin for MusicLyrics bot."""

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot
from config import Config
from MusicLyrics.mongo.sudo_db import add_sudo, remove_sudo, get_sudos


def _is_owner(user_id: int) -> bool:
    return user_id == Config.OWNER_ID


@bot.on_message(filters.command("addsudo"))
async def add_sudo_cmd(client, message: Message):
    """Add a user to sudo list — owner only."""
    if not message.from_user or not _is_owner(message.from_user.id):
        return await message.reply_text(
            "❌ শুধুমাত্র মালিক এই কমান্ড ব্যবহার করতে পারবে।\n"
            "Only the owner can use this command."
        )

    target_id = None

    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name
    else:
        args = message.text.split(None, 1)
        if len(args) > 1:
            try:
                user = await client.get_users(args[1].strip().lstrip("@"))
                target_id = user.id
                target_name = user.first_name
            except Exception:
                try:
                    target_id = int(args[1].strip())
                    target_name = str(target_id)
                except ValueError:
                    return await message.reply_text("❌ ইউজার খুঁজে পাওয়া যায়নি। / User not found.")

    if not target_id:
        return await message.reply_text(
            "❌ ব্যবহার / Usage:\n"
            "`/addsudo <user_id or @username>`\n"
            "অথবা একজন ইউজারের মেসেজে রিপ্লাই দাও।"
        )

    await add_sudo(target_id)
    await message.reply_text(
        f"✅ **{target_name}** (`{target_id}`) কে sudo লিস্টে যোগ করা হয়েছে।\n"
        f"Added to sudo list."
    )


@bot.on_message(filters.command("rmsudo"))
async def rm_sudo_cmd(client, message: Message):
    """Remove a user from sudo list — owner only."""
    if not message.from_user or not _is_owner(message.from_user.id):
        return await message.reply_text(
            "❌ শুধুমাত্র মালিক এই কমান্ড ব্যবহার করতে পারবে।\n"
            "Only the owner can use this command."
        )

    target_id = None

    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name
    else:
        args = message.text.split(None, 1)
        if len(args) > 1:
            try:
                user = await client.get_users(args[1].strip().lstrip("@"))
                target_id = user.id
                target_name = user.first_name
            except Exception:
                try:
                    target_id = int(args[1].strip())
                    target_name = str(target_id)
                except ValueError:
                    return await message.reply_text("❌ ইউজার খুঁজে পাওয়া যায়নি। / User not found.")

    if not target_id:
        return await message.reply_text(
            "❌ ব্যবহার / Usage:\n"
            "`/rmsudo <user_id or @username>`\n"
            "অথবা একজন ইউজারের মেসেজে রিপ্লাই দাও।"
        )

    await remove_sudo(target_id)
    await message.reply_text(
        f"✅ **{target_name}** (`{target_id}`) কে sudo লিস্ট থেকে সরিয়ে দেওয়া হয়েছে।\n"
        f"Removed from sudo list."
    )


@bot.on_message(filters.command("sudolist"))
async def sudo_list_cmd(_, message: Message):
    """Show all sudo users."""
    sudos = await get_sudos()

    if not sudos:
        return await message.reply_text(
            "📋 Sudo লিস্ট খালি। / Sudo list is empty."
        )

    text = "👑 **Sudo Users / সুডো ইউজার:**\n━━━━━━━━━━━━━━━━\n\n"
    for i, s in enumerate(sudos, 1):
        text += f"**{i}.** `{s['user_id']}`\n"

    # Add owner info
    text += f"\n🔱 **Owner:** `{Config.OWNER_ID}`"

    await message.reply_text(text)
