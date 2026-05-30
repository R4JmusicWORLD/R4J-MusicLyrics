"""Main callback query handler for MusicLyrics bot."""

from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from MusicLyrics.bot import bot
from config import Config


@bot.on_callback_query(filters.regex(r"^close$"))
async def close_callback(_, callback: CallbackQuery):
    """Delete the message when the close button is pressed."""
    try:
        await callback.message.delete()
    except Exception:
        await callback.answer("Could not delete message.", show_alert=True)
        return
    await callback.answer("Closed!")


@bot.on_callback_query(filters.regex(r"^noop$"))
async def noop_callback(_, callback: CallbackQuery):
    """No-operation callback for decorative buttons."""
    await callback.answer()


@bot.on_callback_query(filters.regex(r"^start_back$"))
async def start_back_callback(_, callback: CallbackQuery):
    """Go back to start menu."""
    from MusicLyrics.plugins.misc.start import _start_keyboard

    mention = callback.from_user.mention if callback.from_user else "User"
    text = Config.START_TEXT.format(
        mention=mention,
        bot_name=Config.BOT_NAME,
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=_start_keyboard(),
        )
    except Exception:
        try:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=_start_keyboard(),
            )
        except Exception:
            await callback.answer("Could not go back.", show_alert=True)
            return
    await callback.answer()
