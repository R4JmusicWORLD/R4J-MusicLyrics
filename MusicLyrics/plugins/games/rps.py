"""Rock-Paper-Scissors game plugin."""

import random

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

_CHOICES = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
_WINS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

# Active games: {message_id: {"challenger": user_id, "opponent": user_id|None, "mode": str}}
_rps_games: dict[int, dict] = {}


def _rps_keyboard(game_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪨 Rock", callback_data=f"rps_{game_id}_rock"),
            InlineKeyboardButton("📄 Paper", callback_data=f"rps_{game_id}_paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data=f"rps_{game_id}_scissors"),
        ]
    ])


@bot.on_message(filters.command(["rps", "rockpaperscissors"]))
async def rps_cmd(_, message: Message):
    """Start a Rock-Paper-Scissors game.

    Usage:
        /rps — Play against the bot
        /rps @username — Challenge someone
    """
    args = message.text.split(None, 1)
    user = message.from_user

    if len(args) > 1 and args[1].strip().startswith("@"):
        # PvP mode
        opponent_name = args[1].strip()
        sent = await message.reply_text(
            f"✊ **Rock Paper Scissors!**\n\n"
            f"🎯 {user.mention} challenged {opponent_name}!\n"
            f"{opponent_name} — নিচের বাটন থেকে বেছে নাও!\n\n"
            f"(Both players tap your choice below)",
            reply_markup=_rps_keyboard(0),  # placeholder, will update
        )
        _rps_games[sent.id] = {
            "challenger": user.id,
            "challenger_name": user.first_name,
            "opponent_name": opponent_name,
            "opponent": None,
            "choices": {},
            "mode": "pvp",
        }
        # Re-render with correct game_id
        await sent.edit_reply_markup(_rps_keyboard(sent.id))
    else:
        # vs Bot
        sent = await message.reply_text(
            f"✊ **Rock Paper Scissors!**\n\n"
            f"🤖 {user.mention} vs Bot\n"
            f"নিচে থেকে বেছে নাও! / Pick your choice!",
            reply_markup=_rps_keyboard(0),
        )
        _rps_games[sent.id] = {
            "challenger": user.id,
            "challenger_name": user.first_name,
            "choices": {},
            "mode": "bot",
        }
        await sent.edit_reply_markup(_rps_keyboard(sent.id))


@bot.on_callback_query(filters.regex(r"^rps_"))
async def rps_callback(client, callback: CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) != 3:
        return await callback.answer("❌ Invalid", show_alert=True)

    game_id = int(parts[1])
    choice = parts[2]
    user_id = callback.from_user.id

    game = _rps_games.get(game_id)
    if not game:
        return await callback.answer("❌ গেম শেষ হয়ে গেছে। / Game ended.", show_alert=True)

    if game["mode"] == "bot":
        if user_id != game["challenger"]:
            return await callback.answer("❌ এটা তোমার গেম না!", show_alert=True)

        bot_choice = random.choice(list(_CHOICES.keys()))
        player_emoji = _CHOICES[choice]
        bot_emoji = _CHOICES[bot_choice]

        if choice == bot_choice:
            result = "🤝 ড্র! / Draw!"
        elif _WINS[choice] == bot_choice:
            result = "🎉 তুমি জিতেছো! / You win!"
            try:
                await update_score(user_id, "rps", 1)
            except Exception:
                pass
        else:
            result = "😢 বট জিতেছে! / Bot wins!"

        await callback.message.edit_text(
            f"✊ **Rock Paper Scissors Result!**\n\n"
            f"👤 {game['challenger_name']}: {player_emoji}\n"
            f"🤖 Bot: {bot_emoji}\n\n"
            f"**{result}**"
        )
        del _rps_games[game_id]

    elif game["mode"] == "pvp":
        # Record choice
        if user_id in game["choices"]:
            return await callback.answer("তুমি আগেই বেছে নিয়েছো! / Already chosen!", show_alert=True)

        game["choices"][user_id] = choice
        await callback.answer(f"✅ তুমি {_CHOICES[choice]} বেছে নিয়েছো!", show_alert=True)

        # Check if both have chosen
        if len(game["choices"]) >= 2:
            ids = list(game["choices"].keys())
            c1, c2 = game["choices"][ids[0]], game["choices"][ids[1]]
            e1, e2 = _CHOICES[c1], _CHOICES[c2]

            if c1 == c2:
                result = "🤝 ড্র! / Draw!"
            elif _WINS[c1] == c2:
                result = f"🎉 Player 1 জিতেছে!"
                try:
                    await update_score(ids[0], "rps", 1)
                except Exception:
                    pass
            else:
                result = f"🎉 Player 2 জিতেছে!"
                try:
                    await update_score(ids[1], "rps", 1)
                except Exception:
                    pass

            await callback.message.edit_text(
                f"✊ **Rock Paper Scissors Result!**\n\n"
                f"👤 P1: {e1}\n"
                f"👤 P2: {e2}\n\n"
                f"**{result}**"
            )
            del _rps_games[game_id]

    await callback.answer()
