"""Word guessing (hangman-style) game plugin for MusicLyrics bot."""

import asyncio
import random
import time

from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot
from MusicLyrics.mongo.games_db import save_game_score

WORDS = [
    "python", "telegram", "music", "lyrics", "guitar", "piano", "violin",
    "harmony", "melody", "rhythm", "concert", "album", "artist", "singer",
    "microphone", "headphones", "speaker", "amplifier", "frequency",
    "composer", "symphony", "orchestra", "chorus", "verse", "bridge",
    "tempo", "genre", "playlist", "streaming", "download", "podcast",
    "karaoke", "acoustic", "electric", "classic", "jazz", "blues",
    "country", "reggae", "disco", "techno", "remix", "mashup",
    "festival", "stage", "audience", "encore", "ballad", "anthem",
    "soprano", "baritone", "octave", "chord", "scale", "pitch",
    "treble", "bass", "drumstick", "cymbal", "flute", "trumpet",
    "saxophone", "keyboard", "studio", "record", "vinyl", "cassette",
    "equalizer", "reverb", "distortion", "feedback", "soundwave",
    "decibel", "vibration", "resonance", "overtone", "harmony",
]

HINTS = {
    "python": "A programming language named after a snake",
    "telegram": "A messaging app",
    "guitar": "A stringed instrument",
    "piano": "Black and white keys",
    "violin": "Played with a bow",
    "melody": "A sequence of musical notes",
    "rhythm": "The pattern of beats",
    "concert": "A live music performance",
    "karaoke": "Sing along without the vocalist",
    "orchestra": "A large group of musicians",
}

# Active word games: key = chat_id
active_games = {}


def display_word(word, guessed):
    return " ".join(ch if ch in guessed else "▪️" for ch in word)


def format_status(game):
    word_display = display_word(game["word"], game["guessed"])
    wrong = game["wrong"]
    attempts_left = game["max_attempts"] - len(wrong)
    hearts = "❤️" * attempts_left + "🖤" * len(wrong)

    wrong_text = ", ".join(sorted(wrong)) if wrong else "None"
    return (
        f"📝 **Word Seek / শব্দ খোঁজো!**\n\n"
        f"📖 `{word_display}`\n\n"
        f"{hearts}\n"
        f"❌ Wrong: {wrong_text}\n"
        f"🔤 Guessed: {', '.join(sorted(game['guessed'])) or 'None'}\n\n"
        f"⏰ সময় বাকি / Time left: {max(0, int(game['end_time'] - time.time()))}s\n\n"
        f"একটা অক্ষর পাঠাও! / Send a letter to guess!"
    )


@bot.on_message(filters.command(["wordsearch", "wordseek"]))
async def word_seek_start(_, message: Message):
    chat_id = message.chat.id

    if chat_id in active_games:
        await message.reply(
            "⚠️ **এই চ্যাটে ইতিমধ্যে একটা গেম চলছে!**\n"
            "A game is already running in this chat!"
        )
        return

    word = random.choice(WORDS)
    game = {
        "word": word,
        "guessed": set(),
        "wrong": set(),
        "max_attempts": 7,
        "starter_id": message.from_user.id,
        "starter_mention": message.from_user.mention,
        "end_time": time.time() + 120,
        "chat_id": chat_id,
        "hint_given": False,
    }

    active_games[chat_id] = game

    sent = await message.reply(format_status(game))
    game["msg_id"] = sent.id

    # Auto-end timer
    asyncio.create_task(_auto_end(chat_id, 120))


async def _auto_end(chat_id, delay):
    await asyncio.sleep(delay)
    game = active_games.pop(chat_id, None)
    if game:
        try:
            await bot.send_message(
                chat_id,
                f"⏰ **সময় শেষ! / Time's up!**\n\n"
                f"শব্দটি ছিলো / The word was: **{game['word']}**\n\n"
                f"আবার খেলতে /wordsearch দাও!",
            )
        except Exception:
            pass


@bot.on_message(filters.command(["hint"]))
async def hint_cmd(_, message: Message):
    chat_id = message.chat.id
    game = active_games.get(chat_id)
    if not game:
        await message.reply("❌ কোনো গেম চলছে না! / No active game!\nStart one with /wordsearch")
        return

    word = game["word"]

    # Try dictionary hint first
    if word in HINTS and not game["hint_given"]:
        game["hint_given"] = True
        await message.reply(f"💡 **Hint:** {HINTS[word]}")
        return

    # Reveal a random unguessed letter
    unrevealed = [ch for ch in set(word) if ch not in game["guessed"]]
    if unrevealed:
        letter = random.choice(unrevealed)
        game["guessed"].add(letter)
        game["hint_given"] = True

        if all(ch in game["guessed"] for ch in word):
            active_games.pop(chat_id, None)
            await save_game_score(message.from_user.id, "wordsearch", 1, chat_id)
            await message.reply(
                f"🎉 **হিন্ট দিয়ে শব্দটি পাওয়া গেছে!**\n\n"
                f"শব্দ / Word: **{word}**\n"
                f"অভিনন্দন! Congratulations! 🏆"
            )
            return

        await message.reply(
            f"💡 **Hint:** `{letter}` আছে শব্দে!\n\n{format_status(game)}"
        )
    else:
        await message.reply("💡 সব অক্ষর ইতিমধ্যে জানা! / All letters already revealed!")


@bot.on_message(filters.text & filters.group & ~filters.command, group=12)
async def word_seek_guess(_, message: Message):
    chat_id = message.chat.id
    game = active_games.get(chat_id)
    if not game:
        return

    text = message.text.strip().lower()

    # Only process single letter guesses
    if len(text) != 1 or not text.isalpha():
        # Also allow full word guess
        if text == game["word"]:
            active_games.pop(chat_id, None)
            wrong_count = len(game["wrong"])
            score = max(1, game["max_attempts"] - wrong_count)
            await save_game_score(message.from_user.id, "wordsearch", score, chat_id)
            await message.reply(
                f"🎉🎉 **সঠিক! / Correct!**\n\n"
                f"শব্দ / Word: **{game['word']}**\n"
                f"🏆 {message.from_user.mention} জিতেছে!\n"
                f"Score: {score} points!"
            )
            return
        return

    if time.time() > game["end_time"]:
        active_games.pop(chat_id, None)
        await message.reply(
            f"⏰ **সময় শেষ! / Time's up!**\n\n"
            f"শব্দটি ছিলো / The word was: **{game['word']}**"
        )
        return

    letter = text

    if letter in game["guessed"] or letter in game["wrong"]:
        await message.reply(f"⚠️ `{letter}` আগেই চেষ্টা করা হয়েছে! / Already guessed!")
        return

    word = game["word"]
    if letter in word:
        game["guessed"].add(letter)
        if all(ch in game["guessed"] for ch in word):
            active_games.pop(chat_id, None)
            wrong_count = len(game["wrong"])
            score = max(1, game["max_attempts"] - wrong_count)
            await save_game_score(message.from_user.id, "wordsearch", score, chat_id)
            await message.reply(
                f"🎉🎉 **সঠিক! / Correct!**\n\n"
                f"শব্দ / Word: **{word}**\n"
                f"🏆 {message.from_user.mention} জিতেছে!\n"
                f"Score: {score} points!"
            )
            return
        await message.reply(f"✅ `{letter}` আছে! / Correct!\n\n{format_status(game)}")
    else:
        game["wrong"].add(letter)
        if len(game["wrong"]) >= game["max_attempts"]:
            active_games.pop(chat_id, None)
            await message.reply(
                f"💀 **হেরে গেছো! / Game Over!**\n\n"
                f"শব্দটি ছিলো / The word was: **{word}**\n\n"
                f"আবার খেলতে /wordsearch দাও!"
            )
            return
        await message.reply(f"❌ `{letter}` নেই! / Wrong!\n\n{format_status(game)}")
