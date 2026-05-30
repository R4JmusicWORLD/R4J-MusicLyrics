"""Text-to-speech plugin for MusicLyrics bot."""

import os
import asyncio
import tempfile

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot


async def _generate_tts(text: str, lang: str = "en") -> str:
    """Generate TTS audio via gTTS and return file path."""
    from gtts import gTTS
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            None, lambda: gTTS(text=text, lang=lang).save(path)
        )
    except Exception:
        os.remove(path)
        raise
    return path


@bot.on_message(filters.command("tts"))
async def tts_cmd(client, message: Message):
    args = message.text.split(None, 2)

    # Determine language and text
    lang = "en"
    text = ""

    if len(args) >= 3 and len(args[1]) <= 5:
        # /tts bn hello world
        lang = args[1].strip()
        text = args[2].strip()
    elif len(args) >= 2:
        # /tts hello world
        text = message.text.split(None, 1)[1].strip()
    elif message.reply_to_message:
        text = message.reply_to_message.text or message.reply_to_message.caption or ""

    if not text:
        return await message.reply_text(
            "❌ **ব্যবহার / Usage:**\n"
            "`/tts <text>` — English TTS\n"
            "`/tts bn <text>` — Bengali TTS\n"
            "`/tts` (reply to message)\n\n"
            "**Supported:** en, bn, hi, ja, ko, fr, de, es ..."
        )

    status = await message.reply_text("🎙️ ভয়েস তৈরি হচ্ছে... / Generating voice...")

    try:
        path = await _generate_tts(text, lang)
        await message.reply_voice(voice=path, caption=f"🎙️ TTS ({lang})")
        await status.delete()
        os.remove(path)
    except Exception as e:
        await status.edit_text(f"❌ TTS ব্যর্থ। / TTS failed.\nError: `{e}`")
