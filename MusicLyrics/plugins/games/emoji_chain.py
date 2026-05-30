"""Emoji Chain game — remember and repeat growing emoji sequences."""

import random
import asyncio

from pyrogram import filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
)

from MusicLyrics.bot import bot

try:
    from MusicLyrics.mongo.games_db import update_score
except Exception:
    async def update_score(*a, **kw):
        pass

_GAME_EMOJIS = [
    "🍎", "🍊", "🍋", "🍇", "🍉", "🍓", "🫐", "🥝",
    "🌸", "🌻", "⭐", "🌙", "🔥", "💎", "🎵", "🦋",
]

# Active games: message_id -> game state
_chain_games: dict[int, dict] = {}


def _emoji_buttons(game_id: int, options: list[str]) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for emoji in options:
        row.append(InlineKeyboardButton(emoji, callback_data=f"ec_{game_id}_{emoji}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


@bot.on_message(filters.command(["emojichain", "ec"]))
async def emoji_chain_cmd(_, message: Message):
    """Start an Emoji Chain memory game.

    Remember the growing sequence of emojis!
    Each round adds one more emoji to remember.
    """
    user = message.from_user
    if not user:
        return

    # Pick 8 random emojis for this game's pool
    pool = random.sample(_GAME_EMOJIS, 8)
    sequence = [random.choice(pool)]

    sent = await message.reply_text(
        f"🧠 **Emoji Chain / ইমোজি চেইন!**\n\n"
        f"👤 Player: {user.mention}\n"
        f"📝 মনে রাখো এই ইমোজি:\n\n"
        f"**{sequence[0]}**\n\n"
        f"⏳ 3 সেকেন্ড পর বাটন আসবে...",
    )

    game = {
        "user_id": user.id,
        "user_name": user.first_name,
        "pool": pool,
        "sequence": sequence,
        "current_index": 0,  # which emoji in sequence to pick next
        "round": 1,
        "score": 0,
    }
    _chain_games[sent.id] = game

    await asyncio.sleep(3)

    # Show buttons
    await sent.edit_text(
        f"🧠 **Round {game['round']}** — ইমোজিটি বেছে নাও!\n"
        f"Select emoji #{game['current_index'] + 1} of the sequence:",
        reply_markup=_emoji_buttons(sent.id, pool),
    )


@bot.on_callback_query(filters.regex(r"^ec_"))
async def emoji_chain_callback(client, callback: CallbackQuery):
    parts = callback.data.split("_", 2)
    if len(parts) != 3:
        return await callback.answer("❌ Invalid")

    game_id = int(parts[1])
    chosen = parts[2]

    game = _chain_games.get(game_id)
    if not game:
        return await callback.answer("❌ গেম শেষ! / Game ended.", show_alert=True)

    if callback.from_user.id != game["user_id"]:
        return await callback.answer("❌ এটা তোমার গেম না!", show_alert=True)

    expected = game["sequence"][game["current_index"]]

    if chosen != expected:
        # Wrong — game over
        score = game["score"]
        seq_display = " → ".join(game["sequence"])
        del _chain_games[game_id]
        try:
            await update_score(callback.from_user.id, "emojichain", score)
        except Exception:
            pass
        await callback.message.edit_text(
            f"❌ **ভুল! Game Over!**\n\n"
            f"তুমি {chosen} দিয়েছো, কিন্তু সঠিক ছিল {expected}\n\n"
            f"📝 Sequence: {seq_display}\n"
            f"🏆 Score: **{score}** rounds\n\n"
            f"আবার খেলতে: `/emojichain`"
        )
        return await callback.answer("❌ Wrong!", show_alert=True)

    # Correct
    game["current_index"] += 1

    if game["current_index"] >= len(game["sequence"]):
        # Completed this round — add new emoji
        game["round"] += 1
        game["score"] += 1
        game["current_index"] = 0
        new_emoji = random.choice(game["pool"])
        game["sequence"].append(new_emoji)

        seq_display = " → ".join(game["sequence"])

        await callback.message.edit_text(
            f"✅ **Round {game['round'] - 1} Complete!**\n\n"
            f"📝 এবার মনে রাখো:\n"
            f"**{seq_display}**\n\n"
            f"⏳ 3 সেকেন্ড...",
        )
        await callback.answer("✅ Correct!")
        await asyncio.sleep(3)

        await callback.message.edit_text(
            f"🧠 **Round {game['round']}** — পুরো sequence বলো!\n"
            f"Select emoji #{game['current_index'] + 1}:",
            reply_markup=_emoji_buttons(game_id, game["pool"]),
        )
    else:
        # More in sequence to recall
        await callback.answer("✅ Correct! Next...")
        await callback.message.edit_text(
            f"🧠 **Round {game['round']}** — চালিয়ে যাও!\n"
            f"Select emoji #{game['current_index'] + 1}:",
            reply_markup=_emoji_buttons(game_id, game["pool"]),
        )
