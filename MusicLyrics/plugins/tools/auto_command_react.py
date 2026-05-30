"""Global auto-reaction plugin — reacts to ALL bot commands with emoji reactions,
big emoji replies, and random sticker/dice sends.

Uses handler group 97 (very high) so it runs AFTER all real command handlers.
Does NOT use continue_propagation() — just a fire-and-forget watcher.

Compatible with ALL pyrogram versions (no ReactionTypeEmoji dependency).
"""

from __future__ import annotations

import random
import asyncio
import logging
import time

from pyrogram import Client, filters
from pyrogram.types import Message

from MusicLyrics.bot import bot

LOG = logging.getLogger(__name__)

# ── Telegram-supported reaction emojis (large pool) ────────────────────────
REACTION_POOL = [
    "\U0001f44d",  # 👍
    "\U0001f44e",  # 👎
    "\u2764\ufe0f",  # ❤️
    "\U0001f525",  # 🔥
    "\U0001f389",  # 🎉
    "\U0001f929",  # 🤩
    "\U0001f60d",  # 😍
    "\U0001f44f",  # 👏
    "\U0001f970",  # 🥰
    "\U0001f4af",  # 💯
    "\u26a1",      # ⚡
    "\U0001f3c6",  # 🏆
    "\U0001f601",  # 😁
    "\U0001f923",  # 🤣
    "\U0001f44c",  # 👌
    "\U0001f60e",  # 😎
    "\U0001f618",  # 😘
    "\U0001f64f",  # 🙏
    "\U0001f31a",  # 🌚
    "\U0001f37e",  # 🍾
    "\U0001f48b",  # 💋
    "\U0001f607",  # 😇
    "\U0001f92f",  # 🤯
    "\U0001f62d",  # 😭
    "\U0001f608",  # 😈
    "\U0001f440",  # 👀
    "\U0001f47b",  # 👻
    "\U0001f383",  # 🎃
    "\U0001f913",  # 🤓
    "\U0001f633",  # 😳
    "\U0001f353",  # 🍓
    "\U0001f34c",  # 🍌
    "\U0001f494",  # 💔
    "\U0001f648",  # 🙈
    "\U0001f634",  # 😴
    "\U0001f928",  # 🧐
    "\U0001f32d",  # 🌭
    "\U0001f60b",  # 😋
    "\U0001f631",  # 😱
    "\U0001f921",  # 🤡
    "\U0001f973",  # 🥳
    "\U0001f480",  # 💀
    "\u2764\ufe0f\u200d\U0001f525",  # ❤️‍🔥
    "\U0001f54a\ufe0f",  # 🕊️
    "\U0001f911",  # 🤑
    "\U0001f917",  # 🤗
    "\U0001f643",  # 🙃
]

# ── Big emoji grids for reply ───────────────────────────────────────────────
BIG_EMOJI_SETS = [
    "🔥🔥🔥🔥🔥\n🔥🔥🔥🔥🔥\n🔥🔥🔥🔥🔥",
    "⚡⚡⚡⚡⚡\n⚡⚡⚡⚡⚡\n⚡⚡⚡⚡⚡",
    "🎵🎵🎵🎵🎵\n🎵🎵🎵🎵🎵\n🎵🎵🎵🎵🎵",
    "💫💫💫💫💫\n💫💫💫💫💫\n💫💫💫💫💫",
    "🌟🌟🌟🌟🌟\n🌟🌟🌟🌟🌟\n🌟🌟🌟🌟🌟",
    "❤️❤️❤️❤️❤️\n❤️❤️❤️❤️❤️\n❤️❤️❤️❤️❤️",
    "🦋🦋🦋🦋🦋\n🦋🦋🦋🦋🦋\n🦋🦋🦋🦋🦋",
    "✨✨✨✨✨\n✨✨✨✨✨\n✨✨✨✨✨",
    "🎶🎶🎶🎶🎶\n🎶🎶🎶🎶🎶\n🎶🎶🎶🎶🎶",
    "💖💖💖💖💖\n💖💖💖💖💖\n💖💖💖💖💖",
    "🏆🏆🏆🏆🏆\n🏆🏆🏆🏆🏆\n🏆🏆🏆🏆🏆",
    "🎉🎉🎉🎉🎉\n🎉🎉🎉🎉🎉\n🎉🎉🎉🎉🎉",
    "👑👑👑👑👑\n👑👑👑👑👑\n👑👑👑👑👑",
    "🌈🌈🌈🌈🌈\n🌈🌈🌈🌈🌈\n🌈🌈🌈🌈🌈",
    "💎💎💎💎💎\n💎💎💎💎💎\n💎💎💎💎💎",
    "🎸🎸🎸🎸🎸\n🎸🎸🎸🎸🎸\n🎸🎸🎸🎸🎸",
    "🌹🌹🌹🌹🌹\n🌹🌹🌹🌹🌹\n🌹🌹🌹🌹🌹",
    "🍀🍀🍀🍀🍀\n🍀🍀🍀🍀🍀\n🍀🍀🍀🍀🍀",
    "🔮🔮🔮🔮🔮\n🔮🔮🔮🔮🔮\n🔮🔮🔮🔮🔮",
    "🎪🎪🎪🎪🎪\n🎪🎪🎪🎪🎪\n🎪🎪🎪🎪🎪",
]

DICE_EMOJIS = ["🎲", "🎯", "🏀", "⚽", "🎳", "🎰"]

# Cooldown tracker per chat
_last_react_time: dict[int, float] = {}
_REACT_COOLDOWN = 4  # seconds


async def _send_reaction_safe(chat_id: int, message_id: int):
    """Send a random emoji reaction (fire-and-forget, all pyrogram versions)."""
    emoji = random.choice(REACTION_POOL)
    for attempt in range(4):
        try:
            if attempt == 0:
                await bot.send_reaction(chat_id, message_id, emoji=emoji)
            elif attempt == 1:
                await bot.send_reaction(chat_id, message_id, emoji=[emoji])
            elif attempt == 2:
                await bot.send_reaction(chat_id, message_id, reaction=emoji)
            else:
                try:
                    from pyrogram.types import ReactionTypeEmoji
                    await bot.send_reaction(chat_id, message_id, emoji=[ReactionTypeEmoji(emoji=emoji)])
                except ImportError:
                    pass
            return
        except Exception:
            continue


async def _send_big_reaction_and_sticker(chat_id: int, message: Message):
    """Send big emoji grid + sticker/dice as reply (with cooldown)."""
    now = time.time()
    if chat_id in _last_react_time:
        if now - _last_react_time[chat_id] < _REACT_COOLDOWN:
            return
    _last_react_time[chat_id] = now

    # 55% big emoji, 45% dice/sticker
    if random.random() < 0.55:
        emoji_grid = random.choice(BIG_EMOJI_SETS)
        try:
            big_msg = await message.reply_text(emoji_grid)
            await _send_reaction_safe(chat_id, big_msg.id)
        except Exception:
            pass
    else:
        dice_emoji = random.choice(DICE_EMOJIS)
        try:
            dice_msg = await message.reply_dice(emoji=dice_emoji)
            await _send_reaction_safe(chat_id, dice_msg.id)
        except Exception:
            try:
                await message.reply_text(random.choice(BIG_EMOJI_SETS))
            except Exception:
                pass


# ── Watcher handler at group=97 (runs AFTER all real handlers) ──────────────
# This does NOT use continue_propagation(). It sits in a high group number
# so pyrogram runs it after the real command handler in group 0 is done.
# It just adds reactions silently — no interference with actual commands.

@bot.on_message(filters.command([
    "start", "help", "pause", "resume",
    "skip", "next", "stop", "end", "seek", "volume", "vol", "queue",
    "nowplaying", "np", "loop", "shuffle", "song", "vsong", "ping",
    "alive", "ban", "unban", "mute", "unmute", "warn", "antispam",
    "antiflood", "captcha", "blacklist", "setwelcome", "tr", "tts",
    "sticker", "s", "toimg", "kang", "getsticker", "stickerid",
    "info", "chatinfo", "paste", "telegraph", "tagall", "afk",
    "react", "reactall", "emoji", "mixemoji", "randomemoji",
    "broadcast", "stats", "addsudo", "rmsudo", "sudolist",
    "status", "ttt", "quiz", "truth", "dare", "flip", "dice",
    "wordseek", "kill", "pin", "unpin", "purge",
    "filter", "filters", "clearfilter", "notes", "save", "get",
    "emojirain", "emojiart", "emojistory", "emojimood",
    "rps", "guess", "emojichain", "typerace",
    "antilink", "antiraid", "slowmode", "report", "reports",
    "autoreact", "reactpoll", "reactcombo",
    "locks", "lock", "unlock", "nsfw",
    "ai", "ask",
]) & ~filters.edited, group=97)
async def _global_command_reactor(client: Client, message: Message):
    """React to commands with emoji + big emoji/sticker reply.

    Runs in group 97 — AFTER all real handlers. No continue_propagation needed.
    Play commands are excluded (they have their own reactions).
    """
    if not message.from_user:
        return

    chat_id = message.chat.id

    # Add reaction to the original command message
    try:
        await _send_reaction_safe(chat_id, message.id)
    except Exception:
        pass

    # Send big emoji / sticker reply
    try:
        await _send_big_reaction_and_sticker(chat_id, message)
    except Exception:
        pass
