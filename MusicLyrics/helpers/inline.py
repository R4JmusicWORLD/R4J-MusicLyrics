"""Inline keyboard builders for MusicLyrics bot."""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Config


def start_keyboard() -> InlineKeyboardMarkup:
    """Return the start menu inline keyboard."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ Add to Group",
                    url=f"https://t.me/{Config.BOT_NAME}?startgroup=true",
                ),
                InlineKeyboardButton(
                    "🆘 Support",
                    url=Config.SUPPORT_GROUP,
                ),
            ],
            [
                InlineKeyboardButton(
                    "📢 Channel",
                    url=Config.SUPPORT_CHANNEL,
                ),
                InlineKeyboardButton(
                    "👤 Owner",
                    url=Config.OWNER_LINK,
                ),
            ],
            [
                InlineKeyboardButton(
                    "❓ Help & Commands",
                    callback_data="help_main",
                ),
            ],
        ]
    )


def help_keyboard() -> InlineKeyboardMarkup:
    """Return the help categories keyboard."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎵 Music", callback_data="help_music"),
                InlineKeyboardButton("🛡 Admin", callback_data="help_admin"),
            ],
            [
                InlineKeyboardButton("🔒 Security", callback_data="help_security"),
                InlineKeyboardButton("🎮 Games", callback_data="help_games"),
            ],
            [
                InlineKeyboardButton("🛠 Tools", callback_data="help_tools"),
                InlineKeyboardButton("📋 Misc", callback_data="help_misc"),
            ],
            [
                InlineKeyboardButton("◀️ Back", callback_data="start_back"),
                InlineKeyboardButton("✖️ Close", callback_data="close"),
            ],
        ]
    )


def play_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Return playback controls keyboard for a given chat."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
                InlineKeyboardButton("▶️ Resume", callback_data=f"resume_{chat_id}"),
            ],
            [
                InlineKeyboardButton("⏭ Skip", callback_data=f"skip_{chat_id}"),
                InlineKeyboardButton("⏹ Stop", callback_data=f"stop_{chat_id}"),
            ],
        ]
    )


def close_keyboard() -> InlineKeyboardMarkup:
    """Return a simple close button."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✖️ Close", callback_data="close")]]
    )


def back_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    """Return a single back button pointing to *callback_data*."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("◀️ Back", callback_data=callback_data)]]
    )
