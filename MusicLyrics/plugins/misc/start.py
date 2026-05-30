"""Start and help commands for MusicLyrics bot."""

import random

from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)
from pyrogram.enums import ChatType

from MusicLyrics.bot import bot
from config import Config
try:
    from MusicLyrics.mongo.users_db import add_user
except Exception:
    async def add_user(*args, **kwargs):
        pass

import logging

_LOG = logging.getLogger(__name__)

# Start media URLs — randomly chosen on each /start
_START_MEDIA = [
    {"type": "video", "url": "https://image-link.edgeone.app/1779745278298-95x0ue.mp4"},
    {"type": "photo", "url": "https://pic-link-bot.lovable.app/i/telegram-1779340095109-3b9afb55.jpg"},
    {"type": "photo", "url": "https://pic-link-bot.lovable.app/i/telegram-1779340031479-5eab5504.jpg"},
]


def _start_keyboard():
    """Build the start menu inline keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Add Me to Group",
                url=f"https://t.me/{Config.BOT_NAME}?startgroup=true",
            ),
        ],
        [
            InlineKeyboardButton("💬 Support", url=Config.SUPPORT_GROUP),
            InlineKeyboardButton("📢 Channel", url=Config.SUPPORT_CHANNEL),
        ],
        [
            InlineKeyboardButton("👑 Owner", url=Config.OWNER_LINK),
            InlineKeyboardButton("📖 Help", callback_data="help_main"),
        ],
        [
            InlineKeyboardButton("🔒 Close", callback_data="close"),
        ],
    ])


HELP_CATEGORIES = {
    "music": {
        "title": "🎵 Music / মিউজিক",
        "text": (
            "🎵 **Music Commands / মিউজিক কমান্ড:**\n\n"
            "▸ `/play <song>` — Play a song in VC\n"
            "▸ `/vplay <song>` — Play video in VC\n"
            "▸ `/pause` — Pause playback\n"
            "▸ `/resume` — Resume playback\n"
            "▸ `/skip` — Skip current song\n"
            "▸ `/stop` — Stop & leave VC\n"
            "▸ `/queue` — Show queue\n"
            "▸ `/song <query>` — Download song\n"
            "▸ `/vsong <query>` — Download video\n"
        ),
    },
    "games": {
        "title": "🎮 Games / গেমস",
        "text": (
            "🎮 **Game Commands / গেম কমান্ড:**\n\n"
            "▸ `/ttt` — Tic Tac Toe\n"
            "▸ `/quiz` — Start a quiz\n"
            "▸ `/truth` — Truth question\n"
            "▸ `/dare` — Dare challenge\n"
            "▸ `/flip` — Coin flip\n"
            "▸ `/dice` — Roll a dice\n"
            "▸ `/wordseek` — Word seek game\n"
            "▸ `/kill` — Kill game\n"
            "▸ `/rps` — Rock Paper Scissors ✊📄✂️\n"
            "▸ `/guess` — Number guessing game 🔢\n"
            "▸ `/emojichain` — Emoji memory chain 🧠\n"
            "▸ `/typerace` — Typing speed race ⌨️\n"
        ),
    },
    "security": {
        "title": "🔒 Security / সিকিউরিটি",
        "text": (
            "🔒 **Security Commands / সিকিউরিটি কমান্ড:**\n\n"
            "▸ `/ban` — Ban a user\n"
            "▸ `/unban` — Unban a user\n"
            "▸ `/mute` — Mute a user\n"
            "▸ `/unmute` — Unmute a user\n"
            "▸ `/warn` — Warn a user\n"
            "▸ `/antispam` — Toggle anti-spam\n"
            "▸ `/antiflood` — Toggle anti-flood\n"
            "▸ `/captcha` — Toggle captcha\n"
            "▸ `/blacklist` — Manage blacklist\n"
            "▸ `/setwelcome` — Set welcome message\n"
            "▸ `/antilink` — Anti-link protection 🔗\n"
            "▸ `/antiraid` — Anti-raid protection 🛡️\n"
            "▸ `/slowmode` — Slow mode control 🐢\n"
            "▸ `/report` — Report to admins 🚨\n"
            "▸ `/reports` — Toggle report system\n"
        ),
    },
    "tools": {
        "title": "🛠 Tools / টুলস",
        "text": (
            "🛠 **Tool Commands / টুল কমান্ড:**\n\n"
            "▸ `/tr <lang> <text>` — Translate\n"
            "▸ `/tts <text>` — Text to speech\n"
            "▸ `/sticker` — Photo to sticker\n"
            "▸ `/toimg` — Sticker to image\n"
            "▸ `/kang` — Steal sticker\n"
            "▸ `/info` — User info\n"
            "▸ `/chatinfo` — Chat info\n"
            "▸ `/paste` — Paste text online\n"
            "▸ `/telegraph` — Upload to Telegraph\n"
            "▸ `/tagall` — Tag all members\n"
            "▸ `/afk` — Set AFK status\n"
            "▸ `/react` — React to message\n"
            "▸ `/emoji` — Big emoji\n"
            "▸ `/emojirain` — Emoji rain animation 🌧️\n"
            "▸ `/emojiart` — Emoji art patterns 🎨\n"
            "▸ `/emojistory` — Random emoji story 📖\n"
            "▸ `/emojimood` — Random mood emojis 🎭\n"
            "▸ `/autoreact` — Auto-react toggle\n"
            "▸ `/reactpoll` — Reaction-based poll 📊\n"
            "▸ `/reactcombo` — Combo reactions 🎆\n"
        ),
    },
    "admin": {
        "title": "👑 Admin / অ্যাডমিন",
        "text": (
            "👑 **Admin Commands / অ্যাডমিন কমান্ড:**\n\n"
            "▸ `/broadcast` — Broadcast message (sudo)\n"
            "▸ `/stats` — Bot statistics (sudo)\n"
            "▸ `/addsudo` — Add sudo user (owner)\n"
            "▸ `/rmsudo` — Remove sudo user (owner)\n"
            "▸ `/sudolist` — List sudo users\n"
            "▸ `/ping` — Bot latency\n"
            "▸ `/alive` — Bot status\n"
        ),
    },
}


def _help_main_keyboard():
    """Build the help menu inline keyboard."""
    buttons = []
    row = []
    for key, cat in HELP_CATEGORIES.items():
        row.append(InlineKeyboardButton(cat["title"], callback_data=f"help_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔒 Close", callback_data="close")])
    return InlineKeyboardMarkup(buttons)


HELP_MAIN_TEXT = (
    "📖 **Help Menu / হেল্প মেনু**\n\n"
    "নিচের ক্যাটাগরি থেকে বেছে নাও:\n"
    "Choose a category below:\n"
)


@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    """Handle /start command."""
    if message.from_user:
        try:
            await add_user(
                message.from_user.id,
                message.from_user.first_name or "",
                message.from_user.username or "",
            )
        except Exception:
            _LOG.warning("Could not save user to DB (MongoDB may be down).")

    mention = message.from_user.mention if message.from_user else "User"

    if message.chat.type == ChatType.PRIVATE:
        text = Config.START_TEXT.format(
            mention=mention,
            bot_name=Config.BOT_NAME,
        )
        # Send a randomly chosen start media (photo or video)
        chosen = random.choice(_START_MEDIA)
        try:
            if chosen["type"] == "video":
                await client.send_video(
                    message.chat.id,
                    video=chosen["url"],
                    caption="",
                )
            else:
                await client.send_photo(
                    message.chat.id,
                    photo=chosen["url"],
                    caption="",
                )
        except Exception as media_err:
            _LOG.warning("Could not send start media (%s): %s", chosen["url"], media_err)
            # Fallback: try another media
            for fallback in _START_MEDIA:
                if fallback["url"] != chosen["url"]:
                    try:
                        if fallback["type"] == "video":
                            await client.send_video(
                                message.chat.id,
                                video=fallback["url"],
                                caption="",
                            )
                        else:
                            await client.send_photo(
                                message.chat.id,
                                photo=fallback["url"],
                                caption="",
                            )
                        break
                    except Exception:
                        continue
        # Send the text + keyboard as a separate message
        try:
            await message.reply_text(
                text,
                reply_markup=_start_keyboard(),
                disable_web_page_preview=True,
            )
        except Exception:
            await message.reply_text(text, reply_markup=_start_keyboard())
    else:
        await message.reply_text(
            f"🎵 **{Config.BOT_NAME} চালু আছে!**\n\n"
            f"Hey {mention}! সব ফিচার দেখতে আমাকে DM-এ /start দাও।\n"
            f"DM me /start for the full menu!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📖 Help", callback_data="help_main")],
            ]),
        )


@bot.on_message(filters.command("help"))
async def help_cmd(_, message: Message):
    """Handle /help command."""
    await message.reply_text(
        HELP_MAIN_TEXT,
        reply_markup=_help_main_keyboard(),
    )
