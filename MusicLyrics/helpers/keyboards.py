"""Reply keyboard builders for MusicLyrics bot."""

from pyrogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Single-button 'Cancel' reply keyboard."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Cancel")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_keyboard() -> ReplyKeyboardMarkup:
    """Yes / No confirmation reply keyboard."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Yes"), KeyboardButton("No")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Remove any active reply keyboard."""
    return ReplyKeyboardRemove()
