"""Paste service plugin — upload text to a paste service."""

import aiohttp

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot

NEKOBIN_URL = "https://nekobin.com/api/documents"


@bot.on_message(filters.command("paste"))
async def paste_cmd(_, message: Message):
    text = ""
    args = message.text.split(None, 1)
    if len(args) > 1:
        text = args[1].strip()
    elif message.reply_to_message:
        if message.reply_to_message.document:
            doc = await message.reply_to_message.download()
            try:
                with open(doc, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            finally:
                import os
                os.remove(doc)
        else:
            text = message.reply_to_message.text or message.reply_to_message.caption or ""

    if not text:
        return await message.reply_text(
            "❌ পেস্ট করার মতো টেক্সট দাও বা রিপ্লাই দাও।\n"
            "Provide text or reply to a message.\n"
            "Usage: `/paste <text>` or reply `/paste`"
        )

    status = await message.reply_text("📋 পেস্ট করা হচ্ছে... / Pasting...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(NEKOBIN_URL, json={"content": text}) as resp:
                data = await resp.json()
                if "result" in data:
                    key = data["result"]["key"]
                    url = f"https://nekobin.com/{key}"
                    raw_url = f"https://nekobin.com/raw/{key}"
                    await status.edit_text(
                        f"📋 **পেস্ট সফল! / Paste Successful!**\n\n"
                        f"🔗 **Link:** {url}\n"
                        f"📄 **Raw:** {raw_url}"
                    )
                else:
                    await status.edit_text("❌ পেস্ট ব্যর্থ। / Paste failed.")
    except Exception as e:
        await status.edit_text(f"❌ Error: `{e}`")
