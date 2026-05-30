"""Captcha verification plugin for MusicLyrics bot."""

from __future__ import annotations

import asyncio
import hashlib
import random
import logging
import time

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from pyrogram.enums import ChatMemberStatus

from MusicLyrics.bot import bot
from MusicLyrics.mongo.chats_db import get_chat, update_chat_settings
from MusicLyrics.helpers.decorators import admin_required
from config import Config

LOG = logging.getLogger(__name__)

# ── Pending captchas: {chat_id: {user_id: {...}}} ──────────────────────────
_pending: dict[int, dict[int, dict]] = {}

CAPTCHA_TIMEOUT = 300  # 5 minutes


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _get_captcha_settings(chat_id: int) -> tuple[bool, str]:
    doc = await get_chat(chat_id)
    if doc:
        enabled = doc.get("captcha", False)
        mode = doc.get("captcha_mode", "math")
        return enabled, mode
    return False, "math"


def _generate_math_captcha() -> tuple[str, int, list[int]]:
    """Return (question, correct_answer, list_of_4_choices)."""
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    op = random.choice(["+", "-", "*"])
    if op == "+":
        answer = a + b
    elif op == "-":
        answer = a - b
    else:
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        answer = a * b
    question = f"{a} {op} {b} = ?"

    choices = {answer}
    while len(choices) < 4:
        fake = answer + random.randint(-10, 10)
        if fake != answer:
            choices.add(fake)

    choices_list = list(choices)
    random.shuffle(choices_list)
    return question, answer, choices_list


def _generate_button_captcha() -> tuple[str, str, list[str]]:
    """Return (instruction, correct_emoji, list_of_4_emoji_choices)."""
    emoji_map = {
        "apple": "🍎", "banana": "🍌", "cat": "🐱", "dog": "🐶",
        "fish": "🐟", "star": "⭐", "heart": "❤️", "sun": "☀️",
        "moon": "🌙", "tree": "🌳", "flower": "🌸", "fire": "🔥",
    }
    items = random.sample(list(emoji_map.items()), 4)
    correct_name, correct_emoji = items[0]
    emojis = [e for _, e in items]
    random.shuffle(emojis)
    instruction = f"Click the {correct_name} emoji / {correct_name} ইমোজিতে ক্লিক করো"
    return instruction, correct_emoji, emojis


def _generate_text_captcha() -> tuple[str, str, list[str]]:
    """Return (question, correct_answer, list_of_4_choices)."""
    questions = [
        ("বাংলাদেশের রাজধানী কোথায়? / Capital of Bangladesh?", "Dhaka",
         ["Dhaka", "Kolkata", "Mumbai", "Delhi"]),
        ("1 + 1 = ?", "2", ["1", "2", "3", "4"]),
        ("পানির রাসায়নিক সংকেত? / Chemical formula of water?", "H2O",
         ["H2O", "CO2", "O2", "NaCl"]),
        ("সপ্তাহে কত দিন? / Days in a week?", "7",
         ["5", "6", "7", "8"]),
        ("একটি ত্রিভুজের কয়টি বাহু? / Sides of a triangle?", "3",
         ["2", "3", "4", "5"]),
    ]
    q, correct, choices = random.choice(questions)
    random.shuffle(choices)
    return q, correct, choices


def _build_captcha_keyboard(
    chat_id: int, user_id: int, choices: list, correct, mode: str
) -> InlineKeyboardMarkup:
    buttons = []
    for c in choices:
        # Use a hash of the answer value so correct answer is not visible in callback_data
        token = hashlib.sha256(f"{chat_id}_{user_id}_{c}".encode()).hexdigest()[:12]
        cb_data = f"captcha_{chat_id}_{user_id}_{token}"
        buttons.append(InlineKeyboardButton(str(c), callback_data=cb_data))

    # Arrange in 2x2 grid
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


# ── Auto-kick task ──────────────────────────────────────────────────────────

async def _auto_kick_task(client: Client, chat_id: int, user_id: int, msg_id: int):
    await asyncio.sleep(CAPTCHA_TIMEOUT)

    if chat_id in _pending and user_id in _pending[chat_id]:
        _pending[chat_id].pop(user_id, None)
        try:
            await client.ban_chat_member(chat_id, user_id)
            await asyncio.sleep(1)
            await client.unban_chat_member(chat_id, user_id)
        except Exception as e:
            LOG.warning("Captcha auto-kick failed: %s", e)

        try:
            await client.edit_message_text(
                chat_id,
                msg_id,
                f"❌ ইউজার (`{user_id}`) ক্যাপচা সমাধান করেনি এবং কিক হয়েছে।\n"
                f"User failed captcha and was kicked.",
            )
        except Exception:
            pass


# ── New member handler ──────────────────────────────────────────────────────

@bot.on_message(filters.new_chat_members & filters.group)
async def captcha_on_join(client: Client, message: Message):
    chat_id = message.chat.id
    enabled, mode = await _get_captcha_settings(chat_id)
    if not enabled:
        return

    for member in message.new_chat_members:
        if member.is_bot:
            continue

        user_id = member.id

        # Mute until captcha solved
        try:
            await client.restrict_chat_member(
                chat_id, user_id, ChatPermissions()
            )
        except Exception as e:
            LOG.warning("Captcha mute failed: %s", e)
            continue

        # Generate captcha based on mode
        if mode == "button":
            question, correct, choices = _generate_button_captcha()
        elif mode == "text":
            question, correct, choices = _generate_text_captcha()
        else:  # math
            question, correct, choices = _generate_math_captcha()

        keyboard = _build_captcha_keyboard(chat_id, user_id, choices, correct, mode)

        sent = await client.send_message(
            chat_id,
            f"**Captcha Verification**\n\n"
            f"স্বাগতম {member.mention}!\n"
            f"চ্যাটে থাকতে হলে ক্যাপচা সমাধান করো।\n"
            f"Solve the captcha to stay in the chat.\n\n"
            f"**{question}**\n\n"
            f"সময়: {CAPTCHA_TIMEOUT // 60} মিনিট / Time: {CAPTCHA_TIMEOUT // 60} minutes",
            reply_markup=keyboard,
        )

        # Store pending info
        if chat_id not in _pending:
            _pending[chat_id] = {}
        _pending[chat_id][user_id] = {
            "correct": str(correct),
            "msg_id": sent.id,
            "time": time.time(),
        }

        # Schedule auto-kick
        asyncio.create_task(
            _auto_kick_task(client, chat_id, user_id, sent.id)
        )


# ── Captcha callback ───────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^captcha_"))
async def captcha_callback(client: Client, callback: CallbackQuery):
    data = callback.data.split("_")
    # captcha_{chat_id}_{user_id}_{token}
    if len(data) < 4:
        await callback.answer("❌ Invalid captcha data.", show_alert=True)
        return

    chat_id = int(data[1])
    target_user_id = int(data[2])
    token = data[3]

    if callback.from_user.id != target_user_id:
        await callback.answer(
            "এটা তোমার ক্যাপচা না! / This is not your captcha!",
            show_alert=True,
        )
        return

    if chat_id not in _pending or target_user_id not in _pending[chat_id]:
        await callback.answer("ক্যাপচা মেয়াদ শেষ। / Captcha expired.", show_alert=True)
        return

    # Verify answer server-side using stored correct value
    correct = _pending[chat_id][target_user_id]["correct"]
    expected_token = hashlib.sha256(
        f"{chat_id}_{target_user_id}_{correct}".encode()
    ).hexdigest()[:12]
    is_correct = (token == expected_token)

    if is_correct:
        _pending[chat_id].pop(target_user_id, None)

        # Unmute user
        try:
            await client.restrict_chat_member(
                chat_id,
                target_user_id,
                ChatPermissions(
                    can_send_messages=True,
                ),
            )
        except Exception as e:
            LOG.warning("Captcha unmute failed: %s", e)

        await callback.message.edit_text(
            f"**Captcha Solved!**\n"
            f"{callback.from_user.mention} সফলভাবে ভেরিফাই হয়েছে।\n"
            f"Successfully verified! Welcome to the chat."
        )
        await callback.answer("সঠিক! স্বাগতম! / Correct! Welcome!")
    else:
        await callback.answer(
            "❌ ভুল উত্তর! আবার চেষ্টা করো। / Wrong answer! Try again.",
            show_alert=True,
        )


# ── /captcha on/off ─────────────────────────────────────────────────────────

@bot.on_message(filters.command("captcha") & filters.group)
@admin_required
async def captcha_toggle(client: Client, message: Message):
    args = message.command
    if len(args) < 2:
        enabled, mode = await _get_captcha_settings(message.chat.id)
        state = "ON" if enabled else "OFF"
        await message.reply_text(
            f"**Captcha:** {state}\n"
            f"**Mode:** {mode}\n\n"
            f"ব্যবহার / Usage:\n"
            f"`/captcha on` — চালু\n"
            f"`/captcha off` — বন্ধ\n"
            f"`/captcha mode <math/button/text>` — মোড সেট"
        )
        return

    arg = args[1].lower()
    if arg in ("on", "enable", "yes"):
        await update_chat_settings(message.chat.id, {"captcha": True})
        await message.reply_text(
            "**Captcha চালু করা হয়েছে!** / Captcha enabled!\n"
            "নতুন সদস্যদের ক্যাপচা সমাধান করতে হবে।"
        )
    elif arg in ("off", "disable", "no"):
        await update_chat_settings(message.chat.id, {"captcha": False})
        await message.reply_text(
            "**Captcha বন্ধ করা হয়েছে।** / Captcha disabled."
        )
    elif arg == "mode" and len(args) >= 3:
        mode = args[2].lower()
        if mode not in ("math", "button", "text"):
            await message.reply_text(
                "❌ ভুল মোড! `math`, `button`, বা `text` ব্যবহার করো।\n"
                "Invalid mode! Use `math`, `button`, or `text`."
            )
            return
        await update_chat_settings(message.chat.id, {"captcha_mode": mode})
        await message.reply_text(
            f"**Captcha Mode সেট হয়েছে:** `{mode}`"
        )
    else:
        await message.reply_text(
            "Usage: `/captcha on`, `/captcha off`, `/captcha mode <math/button/text>`"
        )
