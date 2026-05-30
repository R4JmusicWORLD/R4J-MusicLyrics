"""Playback control commands and inline callback handlers."""

from __future__ import annotations

import logging

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from MusicLyrics.bot import bot
from MusicLyrics.helpers.filters import not_edited
from MusicLyrics.plugins.play.queue import (
    get_queue,
    get_current,
    clear_queue,
    skip_queue,
    toggle_loop,
    shuffle_queue,
    format_duration,
    get_chat_queue,
)
from MusicLyrics.plugins.play.stream import (
    pause_stream,
    resume_stream,
    seek_stream,
    set_volume,
    leave_voice_chat,
    stream_audio,
    stream_video,
    is_active,
    _now_playing_messages,
    _control_keyboard,
    _get_next_color,
    _get_current_theme,
    _start_progress_timer,
    _stop_progress_timer,
    _get_skip_lock,
    _add_reaction,
    suppress_next_stream_end,
    _fresh_resolve_and_play,
)
from MusicLyrics.utils.autodelete import (
    auto_delete_service,
    auto_delete_playing,
    auto_delete_cmd,
)

LOG = logging.getLogger(__name__)


# ── /pause ───────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("pause") & not_edited)
async def pause_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    if not is_active(chat_id):
        reply = await message.reply_text("❌ কিছু চলছে না এখন।")
        await _add_reaction(chat_id, message.id)
        return
    ok = await pause_stream(chat_id)
    if ok:
        reply = await message.reply_text("⏸ **Paused!**\nResume করতে `/resume` দিন।")
    else:
        reply = await message.reply_text("❌ Pause করা যায়নি।")
    await _add_reaction(chat_id, message.id)


# ── /resume ──────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("resume") & not_edited)
async def resume_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    if not is_active(chat_id):
        reply = await message.reply_text("❌ কিছু চলছে না এখন।")
        await _add_reaction(chat_id, message.id)
        return
    ok = await resume_stream(chat_id)
    if ok:
        reply = await message.reply_text("▶️ **Resumed!**")
    else:
        reply = await message.reply_text("❌ Resume করা যায়নি।")
    await _add_reaction(chat_id, message.id)


# ── /skip | /next ────────────────────────────────────────────────────────────

@bot.on_message(filters.command(["skip", "next"]) & not_edited)
async def skip_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    if not is_active(chat_id):
        reply = await message.reply_text("❌ কিছু চলছে না এখন।")
        await _add_reaction(chat_id, message.id)
        return

    # Acquire skip lock to prevent race with auto-next
    lock = _get_skip_lock(chat_id)
    async with lock:
        # Stop progress timer
        _stop_progress_timer(chat_id)

        # Delete previous "Now Playing" messages
        if chat_id in _now_playing_messages:
            for old_msg in _now_playing_messages[chat_id]:
                try:
                    await old_msg.delete()
                except Exception:
                    pass
            _now_playing_messages[chat_id].clear()

        next_item = await skip_queue(chat_id, force=True)
        if next_item is None:
            await leave_voice_chat(chat_id)
            reply = await message.reply_text(
                "✅ **Queue শেষ হয়ে গেছে!**\n\n"
                "Voice chat থেকে বের হচ্ছি।"
            )
            await _add_reaction(chat_id, message.id)
            return

        try:
            # Suppress the stream-end event that will fire when we replace
            # the current stream — otherwise _on_stream_end double-advances
            suppress_next_stream_end(chat_id)

            # Fresh-resolve media across platforms (YouTube first)
            success = await _fresh_resolve_and_play(chat_id, next_item)
            if not success:
                reply = await message.reply_text("❌ পরের গানে যেতে সমস্যা হয়েছে।")
                await _add_reaction(chat_id, message.id)
                return

            # Start progress timer for the new track
            await _start_progress_timer(chat_id, next_item.duration)

            dur = format_duration(next_item.duration)
            color = _get_next_color()
            t = _get_current_theme()
            reply = await message.reply_text(
                f"⏭ **ꜱᴋɪᴘᴘᴇᴅ!**\n\n"
                f"> {t['title_icon']}  **ᴛɪᴛʟᴇ :** [{next_item.title}]({next_item.url})\n"
                f"> {t['dur_icon']}  **ᴅᴜʀᴀᴛɪᴏɴ :** {dur}\n"
                f"> 👤  **ʀᴇǫᴜᴇꜱᴛᴇᴅ :** {next_item.requester}\n\n"
                f"🦋 ✦ᴘᴏᴡєʀєᴅ ʙʏ » ── [@R4J_81](https://t.me/R4J_81)",
                reply_markup=_control_keyboard(color),
            )
            await _add_reaction(chat_id, message.id)
            # Track this new "Now Playing" message
            if chat_id not in _now_playing_messages:
                _now_playing_messages[chat_id] = []
            _now_playing_messages[chat_id].append(reply)
        except Exception:
            LOG.exception("Skip failed in %s", chat_id)
            reply = await message.reply_text("❌ পরের গানে যেতে সমস্যা হয়েছে।")
            await _add_reaction(chat_id, message.id)


# ── /stop | /end ─────────────────────────────────────────────────────────────

@bot.on_message(filters.command(["stop", "end"]) & not_edited)
async def stop_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    if not is_active(chat_id):
        reply = await message.reply_text("❌ কিছু চলছে না এখন।")
        await _add_reaction(chat_id, message.id)
        return

    # Acquire skip lock to prevent race with auto-next
    lock = _get_skip_lock(chat_id)
    async with lock:
        # Stop progress timer
        _stop_progress_timer(chat_id)

        # Delete previous "Now Playing" messages
        if chat_id in _now_playing_messages:
            for old_msg in _now_playing_messages[chat_id]:
                try:
                    await old_msg.delete()
                except Exception:
                    pass
            _now_playing_messages[chat_id].clear()

        await leave_voice_chat(chat_id)
        reply = await message.reply_text(
            "⏹ **Stopped!**\n\n"
            "✅ Queue clear করে voice chat থেকে বের হয়ে গেছি।"
        )
        await _add_reaction(chat_id, message.id)


# ── /seek <seconds> ──────────────────────────────────────────────────────────

@bot.on_message(filters.command("seek") & not_edited)
async def seek_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    if not is_active(chat_id):
        reply = await message.reply_text("❌ কিছু চলছে না এখন।")
        await _add_reaction(chat_id, message.id)
        return
    if len(message.command) < 2:
        reply = await message.reply_text("**Usage:** `/seek <seconds>`")
        await _add_reaction(chat_id, message.id)
        return
    try:
        seconds = int(message.command[1])
    except ValueError:
        reply = await message.reply_text("❌ সঠিক সংখ্যা দিন। Example: `/seek 30`")
        await _add_reaction(chat_id, message.id)
        return
    ok = await seek_stream(chat_id, seconds)
    if ok:
        reply = await message.reply_text(f"⏩ **{seconds}s** এ seek করা হয়েছে।")
    else:
        reply = await message.reply_text(
            "❌ Seek এখনো এই version-এ fully supported নয়।"
        )
    await _add_reaction(chat_id, message.id)


# ── /volume <1-200> ──────────────────────────────────────────────────────────

@bot.on_message(filters.command(["volume", "vol"]) & not_edited)
async def volume_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    if not is_active(chat_id):
        reply = await message.reply_text("❌ কিছু চলছে না এখন।")
        await _add_reaction(chat_id, message.id)
        return
    if len(message.command) < 2:
        reply = await message.reply_text("**Usage:** `/volume <1-200>`")
        await _add_reaction(chat_id, message.id)
        return
    try:
        vol = int(message.command[1])
    except ValueError:
        reply = await message.reply_text("❌ সঠিক সংখ্যা দিন (1-200)।")
        await _add_reaction(chat_id, message.id)
        return
    if not 1 <= vol <= 200:
        reply = await message.reply_text("❌ Volume 1 থেকে 200 এর মধ্যে হতে হবে।")
        await _add_reaction(chat_id, message.id)
        return
    ok = await set_volume(chat_id, vol)
    if ok:
        reply = await message.reply_text(f"🔊 Volume **{vol}%** সেট হয়েছে।")
    else:
        reply = await message.reply_text("❌ Volume পরিবর্তন করা যায়নি।")
    await _add_reaction(chat_id, message.id)


# ── /queue ───────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("queue") & not_edited)
async def queue_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    items = await get_queue(chat_id)
    if not items:
        reply = await message.reply_text("📜 Queue খালি আছে।")
        await _add_reaction(chat_id, message.id)
        return
    cq = await get_chat_queue(chat_id)
    lines = ["**📜 Current Queue:**\n"]
    for i, item in enumerate(items):
        marker = "▶️" if i == cq.current_index else f"{i + 1}."
        dur = format_duration(item.duration)
        kind = "🎬" if item.stream_type == "video" else "🎵"
        lines.append(f"{marker} {kind} **{item.title}** [{dur}] — {item.requester}")
    loop_status = "🔁 Loop: ON" if cq.loop_mode else "🔁 Loop: OFF"
    lines.append(f"\n{loop_status}")
    reply = await message.reply_text("\n".join(lines))
    await _add_reaction(chat_id, message.id)


# ── /nowplaying | /np ────────────────────────────────────────────────────────

@bot.on_message(filters.command(["nowplaying", "np"]) & not_edited)
async def nowplaying_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    current = await get_current(chat_id)
    if not current:
        reply = await message.reply_text("❌ এখন কিছু চলছে না।")
        await _add_reaction(chat_id, message.id)
        return
    dur = format_duration(current.duration)
    color = _get_next_color()
    t = _get_current_theme()
    text = (
        f"{t['header']} **ᴘʟᴀʏʙᴀᴄᴋ ᴀᴄᴛɪᴠᴀᴛᴇᴅ | ᴇɴᴊᴏʏ ᴛʜᴇ ᴍᴜꜱɪᴄ**\n\n"
        f"> {t['title_icon']}  **ᴛɪᴛʟᴇ :** [{current.title}]({current.url})\n"
        f"> {t['dur_icon']}  **ᴅᴜʀᴀᴛɪᴏɴ :** {dur}\n"
        f"> 👤  **ʀᴇǫᴜᴇꜱᴛᴇᴅ :** {current.requester}\n\n"
        f"🦋 ✦ᴘᴏᴡєʀєᴅ ʙʏ » ── [@R4J_81](https://t.me/R4J_81)"
    )
    if current.thumbnail:
        reply = await bot.send_photo(
            chat_id, photo=current.thumbnail,
            caption=text, reply_markup=_control_keyboard(color),
        )
    else:
        reply = await message.reply_text(text, reply_markup=_control_keyboard(color))
    await _add_reaction(chat_id, message.id)


# ── /loop ────────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("loop") & not_edited)
async def loop_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    state = await toggle_loop(chat_id)
    if state:
        reply = await message.reply_text("🔁 **Loop ON** — বর্তমান গান বারবার চলবে।")
    else:
        reply = await message.reply_text("🔁 **Loop OFF** — Queue স্বাভাবিকভাবে চলবে।")
    await _add_reaction(chat_id, message.id)


# ── /shuffle ─────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("shuffle") & not_edited)
async def shuffle_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    items = await get_queue(chat_id)
    if len(items) < 2:
        reply = await message.reply_text("❌ Shuffle করার জন্য queue-তে কমপক্ষে ২টা গান থাকা দরকার।")
        await _add_reaction(chat_id, message.id)
        return
    await shuffle_queue(chat_id)
    reply = await message.reply_text("🔀 **Queue shuffle হয়ে গেছে!**")
    await _add_reaction(chat_id, message.id)


# ══════════════════════════════════════════════════════════════════════════════
# Callback query handlers (inline keyboard buttons)
# ══════════════════════════════════════════════════════════════════════════════

@bot.on_callback_query(filters.regex(r"^ctl_pause$"))
async def cb_pause(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if not is_active(chat_id):
        try:
            await callback.answer("কিছু চলছে না!", show_alert=True)
        except Exception:
            pass
        return
    ok = await pause_stream(chat_id)
    try:
        await callback.answer("⏸ Paused!" if ok else "❌ Pause failed")
    except Exception:
        pass


@bot.on_callback_query(filters.regex(r"^ctl_resume$"))
async def cb_resume(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if not is_active(chat_id):
        try:
            await callback.answer("কিছু চলছে না!", show_alert=True)
        except Exception:
            pass
        return
    ok = await resume_stream(chat_id)
    try:
        await callback.answer("▶️ Resumed!" if ok else "❌ Resume failed")
    except Exception:
        pass


@bot.on_callback_query(filters.regex(r"^ctl_skip$"))
async def cb_skip(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if not is_active(chat_id):
        try:
            await callback.answer("কিছু চলছে না!", show_alert=True)
        except Exception:
            pass
        return

    # Answer callback IMMEDIATELY to prevent timeout
    try:
        await callback.answer("⏭ Skipping...")
    except Exception:
        pass

    # Acquire skip lock to prevent race with auto-next
    lock = _get_skip_lock(chat_id)
    async with lock:
        if not is_active(chat_id):
            return

        # Stop progress timer
        _stop_progress_timer(chat_id)

        # Delete previous "Now Playing" messages
        if chat_id in _now_playing_messages:
            for old_msg in _now_playing_messages[chat_id]:
                try:
                    await old_msg.delete()
                except Exception:
                    pass
            _now_playing_messages[chat_id].clear()

        next_item = await skip_queue(chat_id, force=True)
        if next_item is None:
            try:
                reply = await callback.message.reply_text(
                    "✅ **Queue শেষ হয়ে গেছে!**\n\n"
                    "Voice chat থেকে বের হচ্ছি।"
                )
            except Exception:
                pass
            await leave_voice_chat(chat_id)
            return

        try:
            # Suppress the stream-end event that will fire when we replace
            # the current stream — otherwise _on_stream_end double-advances
            suppress_next_stream_end(chat_id)

            # Fresh-resolve media across platforms (YouTube first)
            success = await _fresh_resolve_and_play(chat_id, next_item)
            if not success:
                try:
                    err_reply = await callback.message.reply_text("❌ Skip করা যায়নি। আবার চেষ্টা করুন।")
                except Exception:
                    pass
                return

            # Start progress timer for the new track
            await _start_progress_timer(chat_id, next_item.duration)

            dur = format_duration(next_item.duration)
            color = _get_next_color()
            t = _get_current_theme()
            reply = await callback.message.reply_text(
                f"⏭ **ꜱᴋɪᴘᴘᴇᴅ!**\n\n"
                f"> {t['title_icon']}  **ᴛɪᴛʟᴇ :** [{next_item.title}]({next_item.url})\n"
                f"> {t['dur_icon']}  **ᴅᴜʀᴀᴛɪᴏɴ :** {dur}\n"
                f"> 👤  **ʀᴇǫᴜᴇꜱᴛᴇᴅ :** {next_item.requester}\n\n"
                f"🦋 ✦ᴘᴏᴡєʀєᴅ ʙʏ » ── [@R4J_81](https://t.me/R4J_81)",
                reply_markup=_control_keyboard(color),
            )
            # Track this new "Now Playing" message
            if chat_id not in _now_playing_messages:
                _now_playing_messages[chat_id] = []
            _now_playing_messages[chat_id].append(reply)
        except Exception:
            LOG.exception("Skip callback failed in %s", chat_id)
            try:
                err_reply = await callback.message.reply_text("❌ Skip করা যায়নি। আবার চেষ্টা করুন।")
            except Exception:
                pass


@bot.on_callback_query(filters.regex(r"^ctl_stop$"))
async def cb_stop(client: Client, callback: CallbackQuery):
    """CLOSE button — only deletes the Now Playing message, does NOT stop playback."""
    chat_id = callback.message.chat.id

    # Answer callback immediately
    try:
        await callback.answer("✖ Closed")
    except Exception:
        pass

    # Remove this message from the tracking list
    msg_id = callback.message.id
    if chat_id in _now_playing_messages:
        _now_playing_messages[chat_id] = [
            m for m in _now_playing_messages[chat_id] if m.id != msg_id
        ]

    # Delete only this message
    try:
        await callback.message.delete()
    except Exception:
        pass


@bot.on_callback_query(filters.regex(r"^ctl_queue$"))
async def cb_queue(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    items = await get_queue(chat_id)
    if not items:
        try:
            await callback.answer("Queue খালি!", show_alert=True)
        except Exception:
            pass
        return
    cq = await get_chat_queue(chat_id)
    lines = []
    for i, item in enumerate(items):
        marker = "▶️" if i == cq.current_index else f"{i + 1}."
        dur = format_duration(item.duration)
        lines.append(f"{marker} {item.title} [{dur}]")
    text = "\n".join(lines[:15])  # limit to 15 to avoid message length issues
    if len(items) > 15:
        text += f"\n\n... এবং আরো {len(items) - 15}টি গান"
    try:
        await callback.answer(text[:200], show_alert=True)
    except Exception:
        pass


@bot.on_callback_query(filters.regex(r"^ctl_loop$"))
async def cb_loop(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    state = await toggle_loop(chat_id)
    try:
        await callback.answer(
            "🔁 Loop ON" if state else "🔁 Loop OFF",
            show_alert=False,
        )
    except Exception:
        pass
