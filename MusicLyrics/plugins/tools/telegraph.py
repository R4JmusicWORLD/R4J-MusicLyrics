"""Telegraph upload plugin for MusicLyrics bot."""

import os
import aiohttp

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot

TELEGRAPH_UPLOAD_URL = "https://telegra.ph/upload"


@bot.on_message(filters.command("telegraph"))
async def telegraph_cmd(client, message: Message):
    """Upload replied photo or text to Telegraph."""
    reply = message.reply_to_message

    if not reply:
        return await message.reply_text(
            "❌ একটি ফটো বা মেসেজে রিপ্লাই দাও।\n"
            "Reply to a photo or text message.\n"
            "Usage: `/telegraph` (reply)"
        )

    status = await message.reply_text("📤 টেলিগ্রাফে আপলোড হচ্ছে... / Uploading to Telegraph...")

    # Photo upload
    if reply.photo or (reply.document and reply.document.mime_type and reply.document.mime_type.startswith("image/")):
        path = await reply.download()
        try:
            async with aiohttp.ClientSession() as session:
                with open(path, "rb") as f:
                    form = aiohttp.FormData()
                    form.add_field("file", f, filename="image.jpg", content_type="image/jpeg")
                    async with session.post(TELEGRAPH_UPLOAD_URL, data=form) as resp:
                        data = await resp.json()

            if isinstance(data, list) and data:
                url = f"https://telegra.ph{data[0]['src']}"
                await status.edit_text(
                    f"✅ **টেলিগ্রাফে আপলোড সফল! / Upload Successful!**\n\n"
                    f"🔗 **Link:** {url}"
                )
            else:
                await status.edit_text("❌ আপলোড ব্যর্থ। / Upload failed.")
        except Exception as e:
            await status.edit_text(f"❌ Error: `{e}`")
        finally:
            if os.path.exists(path):
                os.remove(path)

    # Text upload — create page via Telegraph API
    elif reply.text:
        text_content = reply.text
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "title": "MusicLyrics Paste",
                    "author_name": "MusicLyrics Bot",
                    "content": [{"tag": "p", "children": [text_content]}],
                    "return_content": "false",
                }
                # Create account first
                async with session.get(
                    "https://api.telegra.ph/createAccount",
                    params={"short_name": "MusicLyrics", "author_name": "MusicLyrics Bot"},
                ) as acc_resp:
                    acc_data = await acc_resp.json()
                    token = acc_data["result"]["access_token"]

                import json
                async with session.post(
                    "https://api.telegra.ph/createPage",
                    data={
                        "access_token": token,
                        "title": "MusicLyrics Paste",
                        "author_name": "MusicLyrics Bot",
                        "content": json.dumps([{"tag": "p", "children": [text_content]}]),
                        "return_content": "false",
                    },
                ) as resp:
                    data = await resp.json()

            if data.get("ok"):
                url = data["result"]["url"]
                await status.edit_text(
                    f"✅ **টেলিগ্রাফ পেজ তৈরি হয়েছে! / Page Created!**\n\n"
                    f"🔗 **Link:** {url}"
                )
            else:
                await status.edit_text("❌ পেজ তৈরি ব্যর্থ। / Page creation failed.")
        except Exception as e:
            await status.edit_text(f"❌ Error: `{e}`")
    else:
        await status.edit_text(
            "❌ শুধু ফটো বা টেক্সট সাপোর্ট করে। / Only photos or text supported."
        )
