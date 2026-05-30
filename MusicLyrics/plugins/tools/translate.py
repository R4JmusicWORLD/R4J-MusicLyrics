"""Translation plugin for MusicLyrics bot using Google Translate."""

import aiohttp

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot

_TR_URL = "https://translate.googleapis.com/translate_a/single"


async def _translate(text: str, target: str, source: str = "auto") -> dict:
    """Translate text via Google Translate unofficial API."""
    params = {
        "client": "gtx",
        "sl": source,
        "tl": target,
        "dt": "t",
        "q": text,
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(_TR_URL, params=params) as resp:
            data = await resp.json()

    translated = "".join(part[0] for part in data[0] if part[0])
    detected = data[2] if len(data) > 2 else source
    return {"text": translated, "src": detected}


@bot.on_message(filters.command("tr"))
async def translate_cmd(_, message: Message):
    args = message.text.split(None, 2)

    # Determine target language and text
    if len(args) >= 3:
        lang = args[1].strip()
        text = args[2].strip()
    elif len(args) == 2 and message.reply_to_message:
        lang = args[1].strip()
        text = message.reply_to_message.text or message.reply_to_message.caption or ""
    else:
        return await message.reply_text(
            "❌ **ব্যবহার / Usage:**\n"
            "`/tr <lang_code> <text>`\n"
            "`/tr <lang_code>` (reply to message)\n\n"
            "**Example:** `/tr en আমি ভালো আছি`\n"
            "**Codes:** en, bn, hi, ja, ko, es, fr, de, ar ..."
        )

    if not text:
        return await message.reply_text("❌ অনুবাদ করার মতো টেক্সট নেই। / No text to translate.")

    status = await message.reply_text("🔄 অনুবাদ করা হচ্ছে... / Translating...")

    try:
        result = await _translate(text, target=lang)
        await status.edit_text(
            f"🌐 **অনুবাদ / Translation**\n\n"
            f"📝 **Source ({result['src']}):**\n`{text}`\n\n"
            f"✅ **Target ({lang}):**\n`{result['text']}`"
        )
    except Exception as e:
        await status.edit_text(f"❌ অনুবাদ ব্যর্থ। / Translation failed.\nError: `{e}`")
