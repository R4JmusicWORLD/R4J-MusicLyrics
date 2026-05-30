"""Song/video download plugin for MusicLyrics bot."""

import os
import asyncio
import re
import logging

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot
from config import Config
from MusicLyrics.plugins.play.platforms.youtube import (
    search_youtube,
    download_audio as yt_download_audio,
    download_video as yt_download_video,
    search_and_download_audio,
    search_and_download_video,
)

LOG = logging.getLogger(__name__)


async def _download(query: str, audio_only: bool = True) -> tuple[str | None, dict | None]:
    """Search YouTube and download audio/video, return (filepath, info).

    Uses search -> download flow first, then falls back to
    search_and_download (atomic yt-dlp search+download) on failure.
    """
    # Method 1: Separate search + download (uses Cobalt/Piped/Invidious)
    info = await search_youtube(query)
    if info:
        url = info.get("url", query)
        try:
            if audio_only:
                filepath = await yt_download_audio(url)
            else:
                filepath = await yt_download_video(url)
            if filepath and os.path.isfile(filepath):
                return filepath, info
        except Exception:
            LOG.warning("Primary download failed for %s, trying atomic fallback", query)

    # Method 2: Atomic search+download via yt-dlp (most reliable fallback)
    LOG.info("Using atomic search+download fallback for: %s", query)
    try:
        if audio_only:
            filepath, info = await search_and_download_audio(query)
        else:
            filepath, info = await search_and_download_video(query)
        if filepath and os.path.isfile(filepath):
            return filepath, info
    except Exception:
        LOG.warning("Atomic search+download also failed for: %s", query)

    return None, info


@bot.on_message(filters.command("song"))
async def song_cmd(client, message: Message):
    """Search and download a song, send as audio."""
    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(
            "**Usage:** `/song <query>`\n\n"
            "Example: `/song Arijit Singh Tum Hi Ho`"
        )

    query = args[1].strip()
    status = await message.reply_text(
        f"🔍 খুঁজছি: **{query}**\nSearching..."
    )

    try:
        await status.edit_text(f"⬇️ ডাউনলোড হচ্ছে... / Downloading: **{query}**")
        path, info = await _download(query, audio_only=True)

        if not path:
            return await status.edit_text(
                "❌ গান খুঁজে পাওয়া যায়নি বা ডাউনলোড ব্যর্থ।\n"
                "Song not found or download failed.\n\n"
                "Tips: Try a different search query or use a direct YouTube URL."
            )

        title = info.get("title", "Unknown") if info else "Unknown"
        duration = info.get("duration", 0) if info else 0
        performer = info.get("channel", info.get("uploader", "Unknown")) if info else "Unknown"

        # Check file size (Telegram limit ~50MB for bots)
        file_size = os.path.getsize(path)
        if file_size > 50 * 1024 * 1024:
            os.remove(path)
            return await status.edit_text(
                "❌ ফাইল সাইজ 50MB এর বেশি। Telegram limit exceeded.\n"
                "Try a shorter song."
            )

        await status.edit_text(f"📤 আপলোড হচ্ছে... / Uploading: **{title}**")
        await message.reply_audio(
            audio=path,
            title=title,
            performer=performer,
            duration=int(duration),
            caption=f"🎵 **{title}**\n🎤 {performer}\n⏱ {int(duration // 60)}:{int(duration % 60):02d}",
        )
        await status.delete()
    except Exception as e:
        LOG.exception("Error in /song command")
        await status.edit_text(f"❌ Error: `{e}`")
    finally:
        if "path" in locals() and path and os.path.exists(path):
            os.remove(path)


@bot.on_message(filters.command("vsong"))
async def vsong_cmd(client, message: Message):
    """Search and download a video, send as video file."""
    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(
            "**Usage:** `/vsong <query>`\n\n"
            "Example: `/vsong Arijit Singh live concert`"
        )

    query = args[1].strip()
    status = await message.reply_text(
        f"🔍 খুঁজছি: **{query}**\nSearching..."
    )

    try:
        await status.edit_text(f"⬇️ ডাউনলোড হচ্ছে... / Downloading: **{query}**")
        path, info = await _download(query, audio_only=False)

        if not path:
            return await status.edit_text(
                "❌ ভিডিও খুঁজে পাওয়া যায়নি বা ডাউনলোড ব্যর্থ।\n"
                "Video not found or download failed.\n\n"
                "Tips: Try a different search query or use a direct YouTube URL."
            )

        title = info.get("title", "Unknown") if info else "Unknown"
        duration = info.get("duration", 0) if info else 0

        # Check file size
        file_size = os.path.getsize(path)
        if file_size > 50 * 1024 * 1024:
            os.remove(path)
            return await status.edit_text(
                "❌ ফাইল সাইজ 50MB এর বেশি। Telegram limit exceeded.\n"
                "Try `/vsong` with a shorter video."
            )

        await status.edit_text(f"📤 আপলোড হচ্ছে... / Uploading: **{title}**")
        await message.reply_video(
            video=path,
            duration=int(duration),
            caption=f"🎬 **{title}**\n⏱ {int(duration // 60)}:{int(duration % 60):02d}",
        )
        await status.delete()
    except Exception as e:
        LOG.exception("Error in /vsong command")
        await status.edit_text(f"❌ Error: `{e}`")
    finally:
        if "path" in locals() and path and os.path.exists(path):
            os.remove(path)
