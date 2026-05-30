"""Reaction features plugin for MusicLyrics bot."""

from pyrogram import filters
from pyrogram.types import Message
try:
    from pyrogram.types import ReactionTypeEmoji
except ImportError:
    ReactionTypeEmoji = None
try:
    from pyrogram.errors import ReactionInvalid, MessageNotModified
except ImportError:
    ReactionInvalid = Exception
    MessageNotModified = Exception

import random
import asyncio
import logging

from MusicLyrics.bot import bot

LOG = logging.getLogger(__name__)

# Actual emoji characters that Telegram supports for reactions
REACTION_EMOJIS = [
    "\U0001f44d",  # 👍 thumbs up
    "\U0001f44e",  # 👎 thumbs down
    "\u2764\ufe0f",  # ❤️ red heart
    "\U0001f525",  # 🔥 fire
    "\U0001f970",  # 🥰 smiling face with hearts
    "\U0001f44f",  # 👏 clapping hands
    "\U0001f601",  # 😁 beaming face
    "\U0001f914",  # 🤔 thinking face
    "\U0001f92f",  # 🤯 exploding head
    "\U0001f631",  # 😱 face screaming
    "\U0001f92c",  # 🤬 face with symbols
    "\U0001f622",  # 😢 crying face
    "\U0001f389",  # 🎉 party popper
    "\U0001f929",  # 🤩 star-struck
    "\U0001f92e",  # 🤮 face vomiting
    "\U0001f4a9",  # 💩 pile of poo
    "\U0001f64f",  # 🙏 folded hands
    "\U0001f44c",  # 👌 OK hand
    "\U0001f54a\ufe0f",  # 🕊️ dove
    "\U0001f921",  # 🤡 clown face
    "\U0001f971",  # 🥱 yawning face
    "\U0001f974",  # 🥴 woozy face
    "\U0001f60d",  # 😍 heart eyes
    "\U0001f433",  # 🐳 spouting whale
    "\u2764\ufe0f\u200d\U0001f525",  # ❤️‍🔥 heart on fire
    "\U0001f31a",  # 🌚 new moon face
    "\U0001f32d",  # 🌭 hot dog
    "\U0001f4af",  # 💯 hundred points
    "\U0001f923",  # 🤣 rolling on floor laughing
    "\u26a1",      # ⚡ high voltage
    "\U0001f34c",  # 🍌 banana
    "\U0001f3c6",  # 🏆 trophy
    "\U0001f494",  # 💔 broken heart
    "\U0001f928",  # 🧐 face with monocle
    "\U0001f610",  # 😐 neutral face
    "\U0001f353",  # 🍓 strawberry
    "\U0001f37e",  # 🍾 bottle with popping cork
    "\U0001f48b",  # 💋 kiss mark
    "\U0001f608",  # 😈 smiling face with horns
    "\U0001f634",  # 😴 sleeping face
    "\U0001f62d",  # 😭 loudly crying face
    "\U0001f913",  # 🤓 nerd face
    "\U0001f47b",  # 👻 ghost
    "\U0001f440",  # 👀 eyes
    "\U0001f383",  # 🎃 jack-o-lantern
    "\U0001f648",  # 🙈 see-no-evil monkey
    "\U0001f607",  # 😇 smiling face with halo
    "\U0001f628",  # 😨 fearful face
    "\U0001f60e",  # 😎 sunglasses
    "\U0001f618",  # 😘 face blowing a kiss
    "\U0001f633",  # 😳 flushed face
    "\U0001f60b",  # 😋 face savoring food
    "\U0001f973",  # 🥳 partying face
    "\U0001f911",  # 🤑 money-mouth face
    "\U0001f917",  # 🤗 hugging face
    "\U0001f643",  # 🙃 upside-down face
    "\U0001f480",  # 💀 skull
    "\U0001f976",  # 🥶 cold face
    "\U0001f975",  # 🥵 hot face
]


async def _send_reaction(client, chat_id, message_id, emoji):
    """Send a reaction with compatibility across ALL Pyrogram versions."""
    # Method 1: plain emoji string
    try:
        await client.send_reaction(
            chat_id=chat_id,
            message_id=message_id,
            emoji=emoji,
        )
        return True
    except Exception:
        pass
    # Method 2: emoji as list
    try:
        await client.send_reaction(
            chat_id=chat_id,
            message_id=message_id,
            emoji=[emoji],
        )
        return True
    except Exception:
        pass
    # Method 3: ReactionTypeEmoji (pyrofork only)
    if ReactionTypeEmoji is not None:
        try:
            await client.send_reaction(
                chat_id=chat_id,
                message_id=message_id,
                emoji=[ReactionTypeEmoji(emoji=emoji)],
            )
            return True
        except Exception:
            pass
    # Method 4: reaction parameter
    try:
        await client.send_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=emoji,
        )
        return True
    except Exception as e:
        LOG.warning("All reaction methods failed: %s", e)
        raise


@bot.on_message(filters.command("react"))
async def react_cmd(client, message: Message):
    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(
            "**Usage:**\n"
            "`/react <emoji>` -- Reply to a message\n"
            "`/react random` -- Random reaction\n"
            "`/react list` -- Available emojis"
        )

    sub = args[1].strip().lower()

    if sub == "list":
        text = "**Available Reactions:**\n\n"
        text += "  ".join(REACTION_EMOJIS)
        return await message.reply_text(text)

    if not message.reply_to_message:
        return await message.reply_text(
            "Reply to a message to react."
        )

    if sub == "random":
        emoji = random.choice(REACTION_EMOJIS)
    else:
        emoji = args[1].strip()

    try:
        await _send_reaction(
            client,
            chat_id=message.chat.id,
            message_id=message.reply_to_message.id,
            emoji=emoji,
        )
        await message.reply_text(f"Reacted with: {emoji}")
    except ReactionInvalid:
        await message.reply_text(
            f"`{emoji}` is not supported for reactions in this chat.\n"
            "Try `/react list` to see available emojis."
        )
    except Exception as e:
        await message.reply_text(f"Error: `{e}`")


@bot.on_message(filters.command("reactall"))
async def reactall_cmd(client, message: Message):
    """React with a random emoji to the replied message."""
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message to react.")

    emoji = random.choice(REACTION_EMOJIS[:20])
    try:
        await _send_reaction(
            client,
            chat_id=message.chat.id,
            message_id=message.reply_to_message.id,
            emoji=emoji,
        )
        await message.reply_text(f"Reacted with: {emoji}")
    except Exception as e:
        await message.reply_text(f"Error: `{e}`")


# --- Auto-react settings per chat ---
_autoreact_chats: dict[int, bool] = {}
_autoreact_rate: dict[int, int] = {}  # chat_id -> percentage (1-100)


@bot.on_message(filters.command("autoreact"))
async def autoreact_cmd(client, message: Message):
    """Toggle automatic reactions on messages.

    Usage:
        /autoreact on [rate]  — Enable auto-react (rate = % chance, default 30)
        /autoreact off        — Disable
        /autoreact status     — Show status
    """
    chat_id = message.chat.id
    args = message.text.split(None, 2)

    if len(args) < 2:
        return await message.reply_text(
            "**Auto-React Usage:**\n\n"
            "▸ `/autoreact on [rate]` — চালু (rate = 1-100%, default 30%)\n"
            "▸ `/autoreact off` — বন্ধ\n"
            "▸ `/autoreact status` — দেখো"
        )

    sub = args[1].strip().lower()

    if sub == "on":
        rate = 30
        if len(args) > 2:
            try:
                rate = max(1, min(100, int(args[2])))
            except ValueError:
                rate = 30
        _autoreact_chats[chat_id] = True
        _autoreact_rate[chat_id] = rate
        await message.reply_text(
            f"✅ Auto-react চালু! / Auto-react enabled!\n"
            f"📊 Rate: {rate}% chance per message"
        )
    elif sub == "off":
        _autoreact_chats[chat_id] = False
        await message.reply_text("❌ Auto-react বন্ধ। / Auto-react disabled.")
    elif sub == "status":
        enabled = _autoreact_chats.get(chat_id, False)
        rate = _autoreact_rate.get(chat_id, 30)
        status = "চালু ✅" if enabled else "বন্ধ ❌"
        await message.reply_text(
            f"**Auto-React Status:**\n\n"
            f"▸ Status: {status}\n"
            f"▸ Rate: {rate}%"
        )
    else:
        await message.reply_text("❌ `/autoreact on|off|status`")


@bot.on_message(filters.group & ~filters.service & ~filters.command([""]), group=20)
async def _autoreact_watcher(client, message: Message):
    """Auto-react to messages if enabled."""
    chat_id = message.chat.id
    if not _autoreact_chats.get(chat_id, False):
        return
    if not message.from_user or message.from_user.is_bot:
        return

    rate = _autoreact_rate.get(chat_id, 30)
    if random.randint(1, 100) > rate:
        return

    emoji = random.choice(REACTION_EMOJIS[:20])
    try:
        await _send_reaction(client, chat_id, message.id, emoji)
    except Exception:
        pass


@bot.on_message(filters.command("reactpoll"))
async def react_poll_cmd(client, message: Message):
    """Create a reaction-based poll using emojis.

    Usage: /reactpoll <question> | <option1 emoji> | <option2 emoji> ...
    Example: /reactpoll Best fruit? | 🍎 | 🍊 | 🍇
    """
    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(
            "**Reaction Poll Usage:**\n\n"
            "`/reactpoll Best fruit? | 🍎 Apple | 🍊 Orange | 🍇 Grape`\n\n"
            "Separate question and options with `|`"
        )

    parts = [p.strip() for p in args[1].split("|")]
    if len(parts) < 3:
        return await message.reply_text(
            "❌ কমপক্ষে 2 টি অপশন দাও। / Need at least 2 options.\n"
            "Example: `/reactpoll Question? | 🍎 Option1 | 🍊 Option2`"
        )

    question = parts[0]
    options = parts[1:]

    text = f"📊 **Reaction Poll / রিঅ্যাকশন পোল**\n\n"
    text += f"❓ {question}\n\n"
    for opt in options:
        text += f"▸ {opt}\n"
    text += f"\n🗳️ নিচের ইমোজি দিয়ে ভোট দাও! / React to vote!"

    await message.reply_text(text)


@bot.on_message(filters.command("reactcombo"))
async def react_combo_cmd(client, message: Message):
    """Send multiple reactions in sequence (animation effect).

    Usage: /reactcombo — Reply to a message
    """
    if not message.reply_to_message:
        return await message.reply_text("Reply to a message to combo react.")

    combo = random.sample(REACTION_EMOJIS[:20], min(5, len(REACTION_EMOJIS)))
    success_count = 0

    for emoji in combo:
        try:
            await _send_reaction(
                client, message.chat.id,
                message.reply_to_message.id, emoji,
            )
            success_count += 1
            await asyncio.sleep(0.5)
        except Exception:
            break

    await message.reply_text(
        f"🎆 Combo React! {success_count} reactions sent!\n"
        f"{'  '.join(combo[:success_count])}"
    )
