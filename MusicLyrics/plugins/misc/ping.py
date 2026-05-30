"""Ping and alive plugin for MusicLyrics bot."""

import time
import platform
import psutil

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot
from config import Config

_START_TIME = time.time()


def _uptime() -> str:
    """Return human-readable uptime."""
    s = int(time.time() - _START_TIME)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


@bot.on_message(filters.command("ping"))
async def ping_cmd(_, message: Message):
    """Show bot latency."""
    start = time.perf_counter()
    sent = await message.reply_text("🏓 Pinging...")
    end = time.perf_counter()
    latency = (end - start) * 1000

    await sent.edit_text(
        f"🏓 **Pong!**\n\n"
        f"⚡ Latency: `{latency:.2f} ms`\n"
        f"⏱ Uptime: `{_uptime()}`"
    )


@bot.on_message(filters.command("alive"))
async def alive_cmd(_, message: Message):
    """Show bot status with system info."""
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)

    text = (
        f"🎵 **{Config.BOT_NAME} — Alive!**\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"🤖 **Bot:** {Config.BOT_NAME}\n"
        f"📌 **Version:** 2.0\n"
        f"⏱ **Uptime:** `{_uptime()}`\n"
        f"🐍 **Python:** `{platform.python_version()}`\n\n"
        f"💻 **System Info:**\n"
        f"▸ CPU: `{cpu}%`\n"
        f"▸ RAM: `{ram.used // (1024**2)} MB / {ram.total // (1024**2)} MB`\n"
        f"▸ RAM Usage: `{ram.percent}%`\n"
        f"▸ OS: `{platform.system()} {platform.release()}`\n\n"
        f"[Support]({Config.SUPPORT_GROUP}) | "
        f"[Channel]({Config.SUPPORT_CHANNEL}) | "
        f"[Owner]({Config.OWNER_LINK})"
    )

    try:
        await message.reply_photo(
            photo=Config.ALIVE_IMG,
            caption=text,
        )
    except Exception:
        await message.reply_text(text)
