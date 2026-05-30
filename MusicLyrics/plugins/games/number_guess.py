"""Number guessing game plugin."""

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

# Active games: {(chat_id, user_id): {number, attempts, max_attempts, start_time, range_max}}
_guess_games: dict[tuple[int, int], dict] = {}


@bot.on_message(filters.command(["guess", "numguess"]))
async def guess_cmd(_, message: Message):
    """Start a number guessing game.

    Usage:
        /guess       — Guess 1-50 (easy)
        /guess hard  — Guess 1-100
        /guess 200   — Custom range 1-200
    """
    user = message.from_user
    if not user:
        return

    key = (message.chat.id, user.id)

    if key in _guess_games:
        game = _guess_games[key]
        return await message.reply_text(
            f"⚠️ তোমার একটা গেম চলছে! 1-{game['range_max']} এর মধ্যে একটি সংখ্যা বলো।\n"
            f"Attempts left: {game['max_attempts'] - game['attempts']}\n"
            f"গেম বাতিল করতে: `/giveup`"
        )

    args = message.text.split(None, 1)
    if len(args) > 1:
        sub = args[1].strip().lower()
        if sub == "hard":
            range_max = 100
            max_attempts = 7
        elif sub == "easy":
            range_max = 50
            max_attempts = 8
        else:
            try:
                range_max = min(max(int(sub), 10), 1000)
                # Scale attempts: log2-ish
                import math
                max_attempts = int(math.log2(range_max)) + 2
            except ValueError:
                range_max = 50
                max_attempts = 8
    else:
        range_max = 50
        max_attempts = 8

    number = random.randint(1, range_max)

    _guess_games[key] = {
        "number": number,
        "attempts": 0,
        "max_attempts": max_attempts,
        "start_time": time.time(),
        "range_max": range_max,
        "hints_given": 0,
    }

    await message.reply_text(
        f"🔢 **Number Guessing Game!**\n\n"
        f"আমি 1 থেকে {range_max} এর মধ্যে একটি সংখ্যা ভেবেছি।\n"
        f"I'm thinking of a number between 1 and {range_max}.\n\n"
        f"🎯 তোমার কাছে **{max_attempts}** বার চেষ্টা আছে!\n"
        f"সংখ্যাটি বলো! Type a number to guess.\n"
        f"Hint: `/ghint` | Give up: `/giveup`"
    )


@bot.on_message(filters.command("ghint"))
async def guess_hint_cmd(_, message: Message):
    """Give a hint for the guessing game."""
    user = message.from_user
    if not user:
        return
    key = (message.chat.id, user.id)
    game = _guess_games.get(key)
    if not game:
        return await message.reply_text("❌ কোনো গেম চলছে না। `/guess` দিয়ে শুরু করো!")

    number = game["number"]
    game["hints_given"] += 1

    if game["hints_given"] == 1:
        parity = "জোড় (even)" if number % 2 == 0 else "বিজোড় (odd)"
        await message.reply_text(f"💡 Hint: সংখ্যাটি {parity}")
    elif game["hints_given"] == 2:
        div3 = "হ্যাঁ ✅" if number % 3 == 0 else "না ❌"
        await message.reply_text(f"💡 Hint: 3 দিয়ে ভাগ যায়? {div3}")
    elif game["hints_given"] == 3:
        mid = game["range_max"] // 2
        half = "প্রথম অর্ধেক (1st half)" if number <= mid else "দ্বিতীয় অর্ধেক (2nd half)"
        await message.reply_text(f"💡 Hint: সংখ্যাটি {half}-এ আছে")
    else:
        await message.reply_text("❌ আর হিন্ট নেই! / No more hints!")


@bot.on_message(filters.command("giveup"))
async def give_up_cmd(_, message: Message):
    """Give up the current guessing game."""
    user = message.from_user
    if not user:
        return
    key = (message.chat.id, user.id)
    game = _guess_games.pop(key, None)
    if not game:
        return await message.reply_text("❌ কোনো গেম চলছে না!")

    await message.reply_text(
        f"😔 হাল ছেড়ে দিলে! / You gave up!\n\n"
        f"🔢 সঠিক উত্তর ছিল: **{game['number']}**"
    )


@bot.on_message(filters.text & filters.group, group=15)
async def _guess_watcher(_, message: Message):
    """Watch for number guesses in active games."""
    user = message.from_user
    if not user or not message.text:
        return

    key = (message.chat.id, user.id)
    game = _guess_games.get(key)
    if not game:
        return

    text = message.text.strip()
    if not text.isdigit():
        return

    guess = int(text)
    number = game["number"]
    game["attempts"] += 1
    attempts = game["attempts"]
    max_attempts = game["max_attempts"]
    remaining = max_attempts - attempts

    if guess == number:
        elapsed = round(time.time() - game["start_time"], 1)
        del _guess_games[key]
        score = max(1, max_attempts - attempts + 1)
        try:
            await update_score(user.id, "numguess", score)
        except Exception:
            pass
        await message.reply_text(
            f"🎉 **সঠিক উত্তর! / Correct!** 🎉\n\n"
            f"🔢 সংখ্যা: **{number}**\n"
            f"🎯 Attempts: {attempts}/{max_attempts}\n"
            f"⏱ সময়: {elapsed}s\n"
            f"⭐ Score: +{score}"
        )
    elif remaining <= 0:
        del _guess_games[key]
        await message.reply_text(
            f"😢 **হেরে গেছো! / Game Over!**\n\n"
            f"🔢 সঠিক সংখ্যা ছিল: **{number}**\n"
            f"আবার চেষ্টা করো: `/guess`"
        )
    elif guess < number:
        await message.reply_text(
            f"⬆️ আরও বড়! / Higher! ({remaining} attempts left)"
        )
    else:
        await message.reply_text(
            f"⬇️ আরও ছোট! / Lower! ({remaining} attempts left)"
        )


@bot.on_message(filters.text & filters.private, group=15)
async def _guess_watcher_pm(_, message: Message):
    """Watch for guesses in private chat too."""
    await _guess_watcher(_, message)
