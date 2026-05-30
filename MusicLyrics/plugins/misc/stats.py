"""Bot statistics plugin (sudo only)."""

import platform
import psutil

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot
from MusicLyrics.helpers.decorators import sudo_required
from MusicLyrics.mongo.users_db import count_users
from MusicLyrics.mongo.chats_db import count_chats
from config import Config


@bot.on_message(filters.command("stats"))
@sudo_required
async def stats_cmd(_, message: Message):
    """Show bot statistics — sudo only."""
    status = await message.reply_text("📊 পরিসংখ্যান লোড হচ্ছে... / Loading stats...")

    total_users = await count_users()
    total_chats = await count_chats()
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)
    disk = psutil.disk_usage("/")

    text = (
        f"📊 **{Config.BOT_NAME} — Statistics**\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"👤 **Total Users:** `{total_users}`\n"
        f"💬 **Total Chats:** `{total_chats}`\n\n"
        f"💻 **System:**\n"
        f"▸ CPU: `{cpu}%`\n"
        f"▸ RAM: `{ram.used // (1024**2)} / {ram.total // (1024**2)} MB ({ram.percent}%)`\n"
        f"▸ Disk: `{disk.used // (1024**3)} / {disk.total // (1024**3)} GB ({disk.percent}%)`\n"
        f"▸ Python: `{platform.python_version()}`\n"
    )

    await status.edit_text(text)
