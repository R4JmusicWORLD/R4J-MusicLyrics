"""Typing Speed Race game — type a phrase as fast as possible."""

import random
import time

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot

try:
    from MusicLyrics.mongo.games_db import update_score
except Exception:
    async def update_score(*a, **kw):
        pass

_PHRASES = [
    "the quick brown fox jumps over the lazy dog",
    "music is the universal language of mankind",
    "every moment is a fresh beginning",
    "life is what happens when you are busy making other plans",
    "in the middle of difficulty lies opportunity",
    "be the change you wish to see in the world",
    "all you need is love and a good playlist",
    "the only way to do great work is to love what you do",
    "imagination is more important than knowledge",
    "stay hungry stay foolish keep learning",
    "coding is like music you compose with logic",
    "telegram bots make life easier for everyone",
    "practice makes a man perfect keep trying",
    "fortune favors the brave and the curious",
    "a journey of thousand miles begins with a single step",
    "not all those who wander are lost",
    "do or do not there is no try",
    "to infinity and beyond the stars await",
    "keep calm and carry on with your dreams",
    "the best time to start is right now today",
    "actions speak louder than words remember that",
    "where there is a will there is a way forward",
    "knowledge is power and sharing it is strength",
    "every expert was once a beginner never give up",
    "the pen is mightier than the sword always",
]

# Bengali phrases
_BN_PHRASES = [
    "জীবন একটি সুন্দর উপহার",
    "স্বপ্ন দেখো এবং সেটা পূরণ করো",
    "সংগীত হলো আত্মার খোরাক",
    "চেষ্টা করো সফলতা আসবেই",
    "পড়াশোনা করো জ্ঞান অর্জন করো",
    "ভালো কাজ করো ভালো ফল পাবে",
    "সময় এবং জোয়ার কারো জন্য অপেক্ষা করে না",
]

# Active races: {(chat_id, user_id): {phrase, start_time}}
_active_races: dict[tuple[int, int], dict] = {}


@bot.on_message(filters.command(["typerace", "typingrace"]))
async def typerace_cmd(_, message: Message):
    """Start a typing speed race.

    Usage:
        /typerace     — English phrase
        /typerace bn  — Bengali phrase
    """
    user = message.from_user
    if not user:
        return

    key = (message.chat.id, user.id)

    if key in _active_races:
        race = _active_races[key]
        return await message.reply_text(
            f"⚠️ তোমার একটি রেস চলছে!\n"
            f"নিচের লেখাটি টাইপ করো:\n\n"
            f"`{race['phrase']}`\n\n"
            f"বাতিল করতে: `/cancelrace`"
        )

    args = message.text.split(None, 1)
    if len(args) > 1 and args[1].strip().lower() == "bn":
        phrase = random.choice(_BN_PHRASES)
    else:
        phrase = random.choice(_PHRASES)

    _active_races[key] = {
        "phrase": phrase,
        "start_time": time.time(),
    }

    word_count = len(phrase.split())

    await message.reply_text(
        f"⌨️ **Typing Race! / টাইপিং রেস!**\n\n"
        f"👤 Player: {user.mention}\n"
        f"📝 Words: {word_count}\n\n"
        f"নিচের লেখাটি যত দ্রুত সম্ভব টাইপ করো:\n"
        f"Type the text below as fast as you can:\n\n"
        f"`{phrase}`\n\n"
        f"⏱ সময় শুরু হয়েছে! / Timer started!\n"
        f"বাতিল: `/cancelrace`"
    )


@bot.on_message(filters.command("cancelrace"))
async def cancel_race_cmd(_, message: Message):
    user = message.from_user
    if not user:
        return
    key = (message.chat.id, user.id)
    if _active_races.pop(key, None):
        await message.reply_text("❌ রেস বাতিল করা হয়েছে। / Race cancelled.")
    else:
        await message.reply_text("❌ কোনো রেস চলছে না!")


@bot.on_message(filters.text & ~filters.command([""]), group=16)
async def _typerace_watcher(_, message: Message):
    """Watch for typing race submissions."""
    user = message.from_user
    if not user or not message.text:
        return

    key = (message.chat.id, user.id)
    race = _active_races.get(key)
    if not race:
        return

    typed = message.text.strip()
    phrase = race["phrase"]

    # Calculate accuracy
    correct_chars = sum(1 for a, b in zip(typed, phrase) if a == b)
    max_len = max(len(typed), len(phrase))
    accuracy = round((correct_chars / max_len) * 100, 1) if max_len > 0 else 0

    elapsed = time.time() - race["start_time"]
    word_count = len(phrase.split())
    wpm = round((word_count / elapsed) * 60, 1) if elapsed > 0 else 0
    cps = round(len(typed) / elapsed, 1) if elapsed > 0 else 0

    # Need at least 70% accuracy
    if accuracy < 70:
        await message.reply_text(
            f"❌ Accuracy অনেক কম! ({accuracy}%)\n"
            f"আবার চেষ্টা করো — পুরো লেখাটি সঠিকভাবে টাইপ করো।"
        )
        return

    del _active_races[key]

    # Grade
    if wpm >= 80:
        grade = "🏆 Legendary!"
    elif wpm >= 60:
        grade = "🥇 Amazing!"
    elif wpm >= 40:
        grade = "🥈 Great!"
    elif wpm >= 25:
        grade = "🥉 Good!"
    else:
        grade = "👍 Keep Practicing!"

    score = int(wpm * accuracy / 100)
    try:
        await update_score(user.id, "typerace", score)
    except Exception:
        pass

    await message.reply_text(
        f"⌨️ **Typing Race Result!**\n\n"
        f"👤 {user.mention}\n"
        f"⏱ Time: **{round(elapsed, 2)}s**\n"
        f"📊 WPM: **{wpm}**\n"
        f"🎯 Accuracy: **{accuracy}%**\n"
        f"⚡ CPS: {cps}\n"
        f"⭐ Score: +{score}\n\n"
        f"**{grade}**"
    )
