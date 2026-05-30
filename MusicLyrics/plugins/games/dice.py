"""Dice game plugin for MusicLyrics bot."""

import random

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction

from MusicLyrics.bot import bot


@bot.on_message(filters.command(["dice"]))
async def dice_cmd(_, message: Message):
    """Roll a dice using Telegram's built-in dice emoji."""
    sent = await message.reply_dice()
    value = sent.dice.value
    await message.reply(
        f"🎲 **Dice Roll!**\n\n"
        f"তোমার ডাইস / Your roll: **{value}**\n\n"
        f"আবার রোল করতে /dice দাও!"
    )


@bot.on_message(filters.command(["roll"]))
async def roll_cmd(_, message: Message):
    """Roll a dice with custom sides."""
    args = message.text.split(None, 1)
    sides = 6
    if len(args) > 1:
        try:
            sides = int(args[1].strip())
            if sides < 2:
                sides = 2
            elif sides > 1000:
                sides = 1000
        except ValueError:
            await message.reply(
                "❌ **সংখ্যা দাও!** / Provide a valid number!\n"
                "Usage: `/roll 20` (2-1000 sides)"
            )
            return

    result = random.randint(1, sides)
    await message.reply(
        f"🎲 **Custom Dice Roll!**\n\n"
        f"🔢 Sides / পাশ: **{sides}**\n"
        f"🎯 Result / ফলাফল: **{result}**\n\n"
        f"আবার রোল করতে `/roll {sides}` দাও!"
    )
