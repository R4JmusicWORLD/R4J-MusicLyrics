"""Coin flip game plugin for MusicLyrics bot."""

import asyncio
import random

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot

COIN_FRAMES = ["🪙 ঘুরছে... / Flipping...", "🪙 .", "🪙 . .", "🪙 . . ."]


@bot.on_message(filters.command(["flip", "coin"]))
async def coin_flip(_, message: Message):
    args = message.text.split(None, 1)
    bet = None
    if len(args) > 1:
        choice = args[1].strip().lower()
        if choice in ("heads", "head", "h"):
            bet = "Heads"
        elif choice in ("tails", "tail", "t"):
            bet = "Tails"

    result = random.choice(["Heads", "Tails"])
    emoji = "🪙" if result == "Heads" else "🎯"

    # Animation
    sent = await message.reply("🪙 কয়েন উল্টাচ্ছি... / Flipping coin...")
    for frame in COIN_FRAMES:
        await asyncio.sleep(0.5)
        try:
            await sent.edit_text(frame)
        except Exception:
            pass

    if bet:
        won = bet == result
        status = "🎉 জিতেছো! / You won!" if won else "😢 হেরেছো! / You lost!"
        await sent.edit_text(
            f"{emoji} **Coin Flip!**\n\n"
            f"Result: **{result}**\n"
            f"তোমার বাজি / Your bet: **{bet}**\n\n"
            f"{status}"
        )
    else:
        await sent.edit_text(
            f"{emoji} **Coin Flip!**\n\n"
            f"ফলাফল / Result: **{result}**\n\n"
            f"বাজি ধরতে চাও? / Want to bet?\n"
            f"`/flip heads` অথবা `/flip tails`"
        )
