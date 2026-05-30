"""Tic Tac Toe game plugin for MusicLyrics bot."""

import asyncio
import math
from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

from MusicLyrics.bot import bot
from MusicLyrics.mongo.games_db import save_game_score

# Active games: key = f"{chat_id}_{msg_id}"
games = {}

EMPTY = " "
X = "❌"
O = "⭕"


def make_board_markup(board, game_id):
    """Build 3x3 inline keyboard from board state."""
    rows = []
    for r in range(3):
        row = []
        for c in range(3):
            idx = r * 3 + c
            cell = board[idx]
            text = cell if cell != EMPTY else "⬜"
            cb = f"ttt_{game_id}_{idx}" if cell == EMPTY else f"ttt_noop"
            row.append(InlineKeyboardButton(text, callback_data=cb))
        rows.append(row)
    rows.append(
        [InlineKeyboardButton("🚫 ত্যাগ করুন / Quit", callback_data=f"ttt_quit_{game_id}")]
    )
    return InlineKeyboardMarkup(rows)


def check_winner(board):
    """Return X, O, 'draw', or None."""
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6),
    ]
    for a, b, c in lines:
        if board[a] == board[b] == board[c] != EMPTY:
            return board[a]
    if EMPTY not in board:
        return "draw"
    return None


# ── Minimax AI ───────────────────────────────────────────────────────────

def minimax(board, is_maximizing):
    result = check_winner(board)
    if result == O:
        return 1
    if result == X:
        return -1
    if result == "draw":
        return 0

    if is_maximizing:
        best = -math.inf
        for i in range(9):
            if board[i] == EMPTY:
                board[i] = O
                best = max(best, minimax(board, False))
                board[i] = EMPTY
        return best
    else:
        best = math.inf
        for i in range(9):
            if board[i] == EMPTY:
                board[i] = X
                best = min(best, minimax(board, True))
                board[i] = EMPTY
        return best


def ai_move(board):
    best_score = -math.inf
    best_idx = None
    for i in range(9):
        if board[i] == EMPTY:
            board[i] = O
            score = minimax(board, False)
            board[i] = EMPTY
            if score > best_score:
                best_score = score
                best_idx = i
    return best_idx


# ── Commands ─────────────────────────────────────────────────────────────

@bot.on_message(filters.command(["ttt", "tictactoe"]))
async def ttt_start(_, message: Message):
    args = message.text.split(None, 1)
    vs_bot = len(args) > 1 and args[1].strip().lower() == "bot"

    if not vs_bot and not message.reply_to_message and not (
        message.entities and len(message.entities) > 1
    ):
        # Check for mentioned user
        mentioned = None
        if message.entities:
            for ent in message.entities:
                if ent.type.value == "mention":
                    username = message.text[ent.offset + 1 : ent.offset + ent.length]
                    try:
                        mentioned = await bot.get_users(username)
                    except Exception:
                        pass
        if message.reply_to_message:
            mentioned = message.reply_to_message.from_user

        if not mentioned and not vs_bot:
            await message.reply(
                "❌ **কাউকে মেনশন করুন বা রিপ্লাই দিন!**\n"
                "Mention someone or reply to play.\n\n"
                "Usage: `/ttt @username` or `/ttt bot`",
            )
            return

    player_x = message.from_user
    player_o = None

    if vs_bot:
        player_o = None  # None means bot
    else:
        # Try to find mentioned user
        mentioned = None
        if message.reply_to_message:
            mentioned = message.reply_to_message.from_user
        elif message.entities:
            for ent in message.entities:
                if ent.type.value == "mention":
                    username = message.text[ent.offset + 1 : ent.offset + ent.length]
                    try:
                        mentioned = await bot.get_users(username)
                    except Exception:
                        pass
        if not mentioned:
            await message.reply(
                "❌ **কাউকে মেনশন করুন বা রিপ্লাই দিন!**\n"
                "Mention someone or reply to play.\n\n"
                "Usage: `/ttt @username` or `/ttt bot`",
            )
            return
        player_o = mentioned

    board = [EMPTY] * 9
    sent = await message.reply(
        f"🎮 **Tic Tac Toe!**\n\n"
        f"{X} — {player_x.mention}\n"
        f"{O} — {'🤖 Bot' if player_o is None else player_o.mention}\n\n"
        f"পালা / Turn: {player_x.mention} ({X})",
        reply_markup=make_board_markup(board, "temp"),
    )

    game_id = f"{sent.chat.id}_{sent.id}"
    games[game_id] = {
        "board": board,
        "turn": X,
        "player_x": player_x.id,
        "player_o": player_o.id if player_o else "bot",
        "player_x_mention": player_x.mention,
        "player_o_mention": "🤖 Bot" if player_o is None else player_o.mention,
        "msg": sent,
        "chat_id": sent.chat.id,
    }

    await sent.edit_reply_markup(make_board_markup(board, game_id))


@bot.on_callback_query(filters.regex(r"^ttt_noop$"))
async def ttt_noop(_, cq: CallbackQuery):
    await cq.answer("এই ঘরটি ইতিমধ্যে দখল করা হয়েছে! / Already taken!", show_alert=False)


@bot.on_callback_query(filters.regex(r"^ttt_quit_"))
async def ttt_quit(_, cq: CallbackQuery):
    game_id = cq.data.replace("ttt_quit_", "")
    game = games.pop(game_id, None)
    if not game:
        await cq.answer("গেম শেষ / Game already ended!", show_alert=True)
        return
    if cq.from_user.id not in (game["player_x"], game["player_o"] if game["player_o"] != "bot" else -1):
        await cq.answer("এটা তোমার গেম না! / Not your game!", show_alert=True)
        return
    await cq.message.edit_text(
        f"🚫 **{cq.from_user.mention} গেম ত্যাগ করেছে!**\nGame forfeited!"
    )


@bot.on_callback_query(filters.regex(r"^ttt_-?\d+_\d+_\d$"))
async def ttt_move(_, cq: CallbackQuery):
    # callback_data format: ttt_{chat_id}_{msg_id}_{cell_idx}
    # chat_id can be negative for groups
    data = cq.data
    last_underscore = data.rfind("_")
    idx = int(data[last_underscore + 1:])
    game_id = data[4:last_underscore]

    game = games.get(game_id)
    if not game:
        await cq.answer("গেম শেষ! / Game ended!", show_alert=True)
        return

    current_symbol = game["turn"]
    expected_player = game["player_x"] if current_symbol == X else game["player_o"]

    if expected_player == "bot":
        await cq.answer("Bot এর পালা! / Bot's turn!", show_alert=True)
        return

    if cq.from_user.id != expected_player:
        await cq.answer("এটা তোমার পালা না! / Not your turn!", show_alert=True)
        return

    board = game["board"]
    if board[idx] != EMPTY:
        await cq.answer("ঘরটি দখল করা আছে! / Cell taken!", show_alert=True)
        return

    board[idx] = current_symbol
    winner = check_winner(board)

    if winner:
        await _finish_game(cq, game, game_id, winner)
        return

    game["turn"] = O if current_symbol == X else X
    next_mention = game["player_o_mention"] if game["turn"] == O else game["player_x_mention"]

    await cq.message.edit_text(
        f"🎮 **Tic Tac Toe!**\n\n"
        f"{X} — {game['player_x_mention']}\n"
        f"{O} — {game['player_o_mention']}\n\n"
        f"পালা / Turn: {next_mention} ({game['turn']})",
        reply_markup=make_board_markup(board, game_id),
    )
    await cq.answer()

    # Bot's turn
    if game["player_o"] == "bot" and game["turn"] == O:
        await asyncio.sleep(1)
        move = ai_move(board)
        if move is not None:
            board[move] = O
            winner = check_winner(board)
            if winner:
                await _finish_game(cq, game, game_id, winner)
                return
            game["turn"] = X
            await cq.message.edit_text(
                f"🎮 **Tic Tac Toe!**\n\n"
                f"{X} — {game['player_x_mention']}\n"
                f"{O} — {game['player_o_mention']}\n\n"
                f"পালা / Turn: {game['player_x_mention']} ({X})",
                reply_markup=make_board_markup(board, game_id),
            )


async def _finish_game(cq, game, game_id, winner):
    games.pop(game_id, None)
    board = game["board"]
    board_text = ""
    for r in range(3):
        for c in range(3):
            cell = board[r * 3 + c]
            board_text += cell if cell != EMPTY else "⬜"
        board_text += "\n"

    if winner == "draw":
        text = (
            f"🎮 **Tic Tac Toe — ড্র! / Draw!**\n\n{board_text}\n"
            f"{X} — {game['player_x_mention']}\n"
            f"{O} — {game['player_o_mention']}\n\n"
            f"🤝 সমান সমান!"
        )
    else:
        winner_id = game["player_x"] if winner == X else game["player_o"]
        winner_mention = game["player_x_mention"] if winner == X else game["player_o_mention"]
        loser_mention = game["player_o_mention"] if winner == X else game["player_x_mention"]
        text = (
            f"🎮 **Tic Tac Toe — বিজয়ী! / Winner!**\n\n{board_text}\n"
            f"🏆 {winner_mention} জিতেছে!\n"
            f"😢 {loser_mention} হেরে গেছে!\n\n"
            f"অভিনন্দন! Congratulations! 🎉"
        )
        if winner_id != "bot":
            await save_game_score(winner_id, "ttt", 1, game["chat_id"])

    await cq.message.edit_text(text)
    await cq.answer()
