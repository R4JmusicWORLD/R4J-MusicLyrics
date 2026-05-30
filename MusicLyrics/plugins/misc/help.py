"""Extended help callback handler for MusicLyrics bot."""

from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from MusicLyrics.bot import bot
from MusicLyrics.plugins.misc.start import HELP_CATEGORIES, HELP_MAIN_TEXT, _help_main_keyboard


@bot.on_callback_query(filters.regex(r"^help_"))
async def help_callback(_, callback: CallbackQuery):
    """Handle help navigation callbacks."""
    data = callback.data

    if data == "help_main":
        await callback.message.edit_text(
            HELP_MAIN_TEXT,
            reply_markup=_help_main_keyboard(),
        )
        await callback.answer()
        return

    # Category pages: help_music, help_games, etc.
    category_key = data.replace("help_", "")
    cat = HELP_CATEGORIES.get(category_key)

    if not cat:
        await callback.answer("❌ Unknown category", show_alert=True)
        return

    # Build navigation — prev/next + back
    keys = list(HELP_CATEGORIES.keys())
    idx = keys.index(category_key)
    nav_row = []

    if idx > 0:
        prev_key = keys[idx - 1]
        nav_row.append(
            InlineKeyboardButton(
                f"◀️ {HELP_CATEGORIES[prev_key]['title']}",
                callback_data=f"help_{prev_key}",
            )
        )

    if idx < len(keys) - 1:
        next_key = keys[idx + 1]
        nav_row.append(
            InlineKeyboardButton(
                f"{HELP_CATEGORIES[next_key]['title']} ▶️",
                callback_data=f"help_{next_key}",
            )
        )

    keyboard = []
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([
        InlineKeyboardButton("🔙 Back / পেছনে", callback_data="help_main"),
        InlineKeyboardButton("🔒 Close", callback_data="close"),
    ])

    try:
        await callback.message.edit_text(
            cat["text"],
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception:
        pass

    await callback.answer()
