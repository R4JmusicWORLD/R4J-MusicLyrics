"""Sticker tools plugin for MusicLyrics bot."""

import os
import tempfile

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import StickersetInvalid

from MusicLyrics.bot import bot


@bot.on_message(filters.command(["sticker", "s"]))
async def to_sticker(client, message: Message):
    """Convert a replied photo to a sticker (webp)."""
    reply = message.reply_to_message
    if not reply or not reply.photo:
        return await message.reply_text(
            "❌ একটি ফটোতে রিপ্লাই দাও। / Reply to a photo."
        )

    status = await message.reply_text("🔄 স্টিকার বানাচ্ছি... / Converting...")
    path = await reply.download()
    try:
        from PIL import Image
        img = Image.open(path).convert("RGBA")
        img.thumbnail((512, 512))
        webp_path = path + ".webp"
        img.save(webp_path, "WEBP")
        await message.reply_sticker(sticker=webp_path)
        await status.delete()
        os.remove(webp_path)
    except Exception as e:
        await status.edit_text(f"❌ Error: `{e}`")
    finally:
        if os.path.exists(path):
            os.remove(path)


@bot.on_message(filters.command("toimg"))
async def sticker_to_img(client, message: Message):
    """Convert a replied sticker to a PNG image."""
    reply = message.reply_to_message
    if not reply or not reply.sticker:
        return await message.reply_text(
            "❌ একটি স্টিকারে রিপ্লাই দাও। / Reply to a sticker."
        )
    if reply.sticker.is_animated or reply.sticker.is_video:
        return await message.reply_text(
            "❌ অ্যানিমেটেড/ভিডিও স্টিকার সাপোর্ট করে না।\n"
            "Animated/video stickers not supported."
        )

    status = await message.reply_text("🔄 ইমেজে কনভার্ট করছি... / Converting...")
    path = await reply.download()
    try:
        from PIL import Image
        img = Image.open(path).convert("RGBA")
        png_path = path + ".png"
        img.save(png_path, "PNG")
        await message.reply_photo(photo=png_path)
        await status.delete()
        os.remove(png_path)
    except Exception as e:
        await status.edit_text(f"❌ Error: `{e}`")
    finally:
        if os.path.exists(path):
            os.remove(path)


@bot.on_message(filters.command("getsticker"))
async def get_sticker(client, message: Message):
    """Get a replied sticker as a document file."""
    reply = message.reply_to_message
    if not reply or not reply.sticker:
        return await message.reply_text(
            "❌ একটি স্টিকারে রিপ্লাই দাও। / Reply to a sticker."
        )

    path = await reply.download()
    try:
        await message.reply_document(
            document=path,
            caption="📎 এই নাও স্টিকার ফাইল। / Here is the sticker file."
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")
    finally:
        if os.path.exists(path):
            os.remove(path)


@bot.on_message(filters.command("stickerid"))
async def sticker_id(_, message: Message):
    """Get the file_id of a replied sticker."""
    reply = message.reply_to_message
    if not reply or not reply.sticker:
        return await message.reply_text(
            "❌ একটি স্টিকারে রিপ্লাই দাও। / Reply to a sticker."
        )

    await message.reply_text(
        f"🆔 **Sticker File ID:**\n`{reply.sticker.file_id}`"
    )


@bot.on_message(filters.command("kang"))
async def kang_sticker(client, message: Message):
    """Steal/add a sticker to the user's personal sticker pack."""
    reply = message.reply_to_message
    if not reply:
        return await message.reply_text(
            "❌ একটি স্টিকার বা ফটোতে রিপ্লাই দাও। / Reply to a sticker or photo."
        )

    user = message.from_user
    status = await message.reply_text("🔄 স্টিকার কাং করছি... / Kanging sticker...")

    # Download and prepare the sticker image
    path = None
    sticker_emoji = "🤩"
    try:
        if reply.sticker:
            if reply.sticker.is_animated or reply.sticker.is_video:
                return await status.edit_text(
                    "❌ অ্যানিমেটেড/ভিডিও স্টিকার কাং করা যাচ্ছে না।\n"
                    "Cannot kang animated/video stickers."
                )
            path = await reply.download()
            sticker_emoji = reply.sticker.emoji or "🤩"
        elif reply.photo:
            path = await reply.download()
        else:
            return await status.edit_text(
                "❌ শুধু স্টিকার বা ফটো কাং করা যায়। / Only stickers or photos."
            )

        from PIL import Image
        img = Image.open(path).convert("RGBA")
        img.thumbnail((512, 512))
        webp_path = path + "_kang.webp"
        img.save(webp_path, "WEBP")

        pack_name = f"ml_{user.id}_by_{(await client.get_me()).username}"
        pack_title = f"{user.first_name}'s MusicLyrics Pack"

        try:
            # Try adding to existing pack using raw API
            from pyrogram.raw.functions.stickers import AddStickerToSet
            from pyrogram.raw.types import (
                InputStickerSetShortName,
                InputStickerSetItem,
            )
            saved_file = await client.save_file(webp_path)
            await client.invoke(
                AddStickerToSet(
                    stickerset=InputStickerSetShortName(short_name=pack_name),
                    sticker=InputStickerSetItem(
                        document=saved_file,
                        emoji=sticker_emoji,
                    ),
                )
            )
        except Exception:
            # Pack doesn't exist — send the sticker as document for manual add
            await message.reply_document(
                document=webp_path,
                caption=(
                    f"📎 স্টিকারটি এখানে আছে। নিজে প্যাকে যোগ করো!\n"
                    f"Here's the sticker. Add it to your pack manually!\n\n"
                    f"Emoji: {sticker_emoji}"
                ),
            )
            await status.delete()
            for p in [path, webp_path]:
                if p and os.path.exists(p):
                    os.remove(p)
            return

        await status.edit_text(
            f"✅ স্টিকার কাং করা হয়েছে! / Sticker kanged!\n\n"
            f"📦 Pack: [Open Pack](https://t.me/addstickers/{pack_name})\n"
            f"😎 Emoji: {sticker_emoji}"
        )

        for p in [path, webp_path]:
            if p and os.path.exists(p):
                os.remove(p)

    except Exception as e:
        await status.edit_text(f"❌ Kang failed: `{e}`")
        if path and os.path.exists(path):
            os.remove(path)
