"""Emoji tools plugin for MusicLyrics bot."""

import random
import asyncio

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot

EMOJI_LIST = [
    "\U0001f600", "\U0001f602", "\U0001f970", "\U0001f60e", "\U0001f929",
    "\U0001f621", "\U0001f97a", "\U0001f62d", "\U0001f92f", "\U0001fae1",
    "\U0001f47b", "\U0001f480", "\U0001f916", "\U0001f47d", "\U0001f383",
    "\U0001f525", "\U0001f496", "\u2b50", "\U0001f308", "\U0001f3b5",
    "\U0001f98b", "\U0001f409", "\U0001f355", "\U0001f3ae", "\U0001f3c6",
    "\U0001f48e", "\U0001f680", "\U0001f338", "\U0001f340", "\U0001f984",
]

# Emoji art patterns
_EMOJI_ART = {
    "heart": [
        " {e} {e}   {e} {e} ",
        "{e} {e} {e} {e} {e} {e}",
        "{e} {e} {e} {e} {e} {e}",
        " {e} {e} {e} {e} {e} ",
        "  {e} {e} {e} {e}  ",
        "   {e} {e} {e}   ",
        "    {e} {e}    ",
        "     {e}     ",
    ],
    "star": [
        "     {e}     ",
        "    {e}{e}{e}    ",
        "   {e} {e} {e}   ",
        "{e}{e}{e}{e}{e}{e}{e}{e}{e}",
        " {e} {e}   {e} {e} ",
        "  {e} {e} {e} {e}  ",
        " {e}{e}   {e}{e} ",
        "{e} {e}     {e} {e}",
    ],
    "diamond": [
        "    {e}    ",
        "   {e} {e}   ",
        "  {e}   {e}  ",
        " {e}     {e} ",
        "{e}       {e}",
        " {e}     {e} ",
        "  {e}   {e}  ",
        "   {e} {e}   ",
        "    {e}    ",
    ],
    "smile": [
        " {e}{e}{e}{e}{e}{e} ",
        "{e}      {e}",
        "{e} {e}  {e} {e}",
        "{e}      {e}",
        "{e} {e}  {e} {e}",
        "{e}  {e}{e}  {e}",
        " {e}{e}{e}{e}{e}{e} ",
    ],
    "wave": [
        "{e}     {e}     {e}",
        " {e}   {e} {e}   {e}",
        "  {e} {e}   {e} {e}",
        "   {e}     {e}",
    ],
}


@bot.on_message(filters.command("emoji"))
async def emoji_cmd(_, message: Message):
    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(
            "Provide an emoji.\n"
            "Example: `/emoji \U0001f525`"
        )

    emoji = args[1].strip()
    big = (
        f"{emoji} {emoji} {emoji} {emoji} {emoji}\n"
        f"{emoji} {emoji} {emoji} {emoji} {emoji}\n"
        f"{emoji} {emoji} {emoji} {emoji} {emoji}\n"
        f"{emoji} {emoji} {emoji} {emoji} {emoji}\n"
        f"{emoji} {emoji} {emoji} {emoji} {emoji}"
    )
    await message.reply_text(big)


@bot.on_message(filters.command("mixemoji"))
async def mix_emoji_cmd(_, message: Message):
    args = message.text.split(None, 2)
    if len(args) < 3:
        return await message.reply_text(
            "Provide two emojis.\n"
            "Example: `/mixemoji \U0001f525 \U0001f4a7`"
        )

    e1, e2 = args[1].strip(), args[2].strip()
    combos = [
        f"{e1} + {e2} = {e1}{e2} \u2728",
        f"{e2} + {e1} = {e2}{e1} \U0001f4ab",
        f"{e1} x {e2} = {e1} \U0001f91d {e2}",
    ]
    text = (
        f"**Emoji Mix**\n\n"
        + "\n".join(combos)
        + f"\n\nMixed result: {e1}{e2}{random.choice(EMOJI_LIST)}"
    )
    await message.reply_text(text)


@bot.on_message(filters.command("randomemoji"))
async def random_emoji_cmd(_, message: Message):
    picked = random.sample(EMOJI_LIST, k=min(5, len(EMOJI_LIST)))
    await message.reply_text(
        f"**Random Emoji:**\n\n"
        f"{'  '.join(picked)}"
    )


@bot.on_message(filters.command("emojirain"))
async def emoji_rain_cmd(_, message: Message):
    """Send a cascade of random emojis — an emoji rain animation.

    Usage: /emojirain [emoji] [count]
    """
    args = message.text.split(None, 2)
    emoji = args[1].strip() if len(args) > 1 else None
    count = 5

    if len(args) > 2:
        try:
            count = min(int(args[2]), 8)
        except ValueError:
            count = 5

    if not emoji:
        pool = random.sample(EMOJI_LIST, min(10, len(EMOJI_LIST)))
    else:
        pool = [emoji]

    status = await message.reply_text("🌧️")

    frames = []
    for i in range(count):
        line_count = min(i + 2, 6)
        lines = []
        for _ in range(line_count):
            spacing = random.randint(0, 3)
            emojis = [random.choice(pool) for _ in range(random.randint(3, 7))]
            lines.append((" " * spacing) + " ".join(emojis))
        frames.append("\n".join(lines))

    for frame in frames:
        try:
            await status.edit_text(frame)
            await asyncio.sleep(0.8)
        except Exception:
            break

    # Final frame
    final_emojis = " ".join(random.choice(pool) for _ in range(15))
    try:
        await status.edit_text(
            f"🌧️ **Emoji Rain Complete!**\n\n{final_emojis}"
        )
    except Exception:
        pass


@bot.on_message(filters.command("emojiart"))
async def emoji_art_cmd(_, message: Message):
    """Create emoji art patterns.

    Usage:
        /emojiart heart 🔥
        /emojiart star ⭐
        /emojiart diamond 💎
        /emojiart smile 😊
        /emojiart wave 🌊
    """
    args = message.text.split(None, 2)
    if len(args) < 2:
        shapes = ", ".join(f"`{s}`" for s in _EMOJI_ART.keys())
        return await message.reply_text(
            f"**Emoji Art / ইমোজি আর্ট**\n\n"
            f"Usage: `/emojiart <shape> [emoji]`\n\n"
            f"Shapes: {shapes}\n"
            f"Example: `/emojiart heart ❤️`"
        )

    shape = args[1].strip().lower()
    emoji = args[2].strip() if len(args) > 2 else "❤️"

    pattern = _EMOJI_ART.get(shape)
    if not pattern:
        shapes = ", ".join(f"`{s}`" for s in _EMOJI_ART.keys())
        return await message.reply_text(
            f"❌ Unknown shape. Available: {shapes}"
        )

    art = "\n".join(line.replace("{e}", emoji) for line in pattern)
    await message.reply_text(art)


@bot.on_message(filters.command("emojistory"))
async def emoji_story_cmd(_, message: Message):
    """Generate a random story told entirely in emojis."""
    stories = [
        "👶 ➡️ 🏫 ➡️ 📚 ➡️ 🎓 ➡️ 💼 ➡️ 💰 ➡️ 🏠 ➡️ 💍 ➡️ 👨‍👩‍👧‍👦 ➡️ 😊",
        "🌅 ➡️ ☕ ➡️ 💻 ➡️ 😤 ➡️ 🍕 ➡️ 💻 ➡️ ✅ ➡️ 🎮 ➡️ 😴",
        "🏃 ➡️ 🌧️ ➡️ 🏠 ➡️ ☕ ➡️ 📺 ➡️ 🍿 ➡️ 😊 ➡️ 💤",
        "💑 ➡️ 🎭 ➡️ 🍽️ ➡️ 🌃 ➡️ 💃 ➡️ 🎵 ➡️ 💋 ➡️ ❤️",
        "🐱 ➡️ 📦 ➡️ 😺 ➡️ 🧶 ➡️ 😸 ➡️ 🐟 ➡️ 😻 ➡️ 💤",
        "🧑‍🚀 ➡️ 🚀 ➡️ 🌍 ➡️ ✨ ➡️ 🌙 ➡️ 👽 ➡️ 🤝 ➡️ 🏠",
        "🎸 ➡️ 🎤 ➡️ 🎵 ➡️ 🎶 ➡️ 👏 ➡️ 🏆 ➡️ 🌟 ➡️ 🎉",
        "🌱 ➡️ 🌿 ➡️ 🌳 ➡️ 🍎 ➡️ 🍏 ➡️ 🧃 ➡️ 😋",
    ]
    story = random.choice(stories)
    await message.reply_text(
        f"📖 **Emoji Story:**\n\n{story}"
    )


@bot.on_message(filters.command("emojimood"))
async def emoji_mood_cmd(_, message: Message):
    """Show a random mood with matching emojis.

    Usage: /emojimood
    """
    moods = [
        ("Happy / খুশি", "😊 🎉 ✨ 🌟 💃 🎵 🥳 🌈"),
        ("Sad / দুঃখিত", "😢 💔 🌧️ 😔 🥺 💧 🫂 😞"),
        ("Angry / রাগ", "😤 🔥 💢 😡 👊 ⚡ 🌋 💥"),
        ("Love / ভালোবাসা", "❤️ 💕 🥰 😍 💋 🌹 💝 💞"),
        ("Sleepy / ঘুম", "😴 💤 🌙 🛏️ 🌃 ☕ 🥱 😪"),
        ("Excited / উত্তেজিত", "🤩 🎊 🚀 ⭐ 🎆 🎇 💫 🔥"),
        ("Chill / রিল্যাক্স", "😎 🏖️ 🎧 ☀️ 🍹 🌴 🧊 🎶"),
        ("Hungry / ক্ষুধা", "😋 🍕 🍔 🍟 🍩 🌮 🍣 🤤"),
        ("Studious / পড়াশোনা", "📚 📝 💡 🎓 🧠 📖 ✏️ 🤓"),
        ("Creative / সৃজনশীল", "🎨 ✍️ 🎭 🎬 📷 🎸 🖌️ 💡"),
    ]
    mood_name, emojis = random.choice(moods)
    await message.reply_text(
        f"🎭 **Mood: {mood_name}**\n\n{emojis}"
    )
