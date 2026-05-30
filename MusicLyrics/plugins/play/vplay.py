"""Handler for /vplay <query|url> — video playback in voice chat.

Uses stream URL extraction as primary method (no download needed),
with download as fallback. Based on patterns from YukkiMusicBot.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from MusicLyrics.bot import bot
from MusicLyrics.helpers.filters import not_edited
from config import Config

from MusicLyrics.plugins.play.queue import (
    QueueItem,
    add_to_queue,
    get_chat_queue,
    format_duration,
)
from MusicLyrics.plugins.play.stream import (
    stream_video,
    is_active,
    pre_join_vc,
    _now_playing_messages,
    _control_keyboard,
    _get_next_color,
    _get_current_theme,
    _start_progress_timer,
    _add_reaction,
)
from MusicLyrics.plugins.play.platforms.youtube import (
    search_youtube,
    get_video_stream_url,
    download_video,
    get_video_info,
    is_youtube_url,
    search_and_download_video,
)
from MusicLyrics.plugins.play.platforms.spotify import (
    is_spotify_url,
    get_spotify_track,
)
from MusicLyrics.plugins.play.platforms.jiosaavn import (
    is_jiosaavn_url,
    get_jiosaavn_song,
    search_and_download_jiosaavn,
    search_jiosaavn,
)
from MusicLyrics.plugins.play.platforms.apple_music import (
    is_apple_music_url,
    get_apple_music_track,
)
from MusicLyrics.plugins.play.platforms.soundcloud import (
    is_soundcloud_url,
    get_soundcloud_info,
    download_soundcloud,
    get_soundcloud_stream_url,
    search_and_download_soundcloud,
)
from MusicLyrics.plugins.play.play import _detect_platform
from MusicLyrics.utils.autodelete import (
    auto_delete_service,
    auto_delete_playing,
    auto_delete_cmd,
)

LOG = logging.getLogger(__name__)


async def _get_video_media(url: str) -> tuple[str, bool]:
    """Get media path for video playback.

    Returns (media_path, is_stream_url).
    SPEED OPTIMISED: Stream URL first (instant playback, no download wait),
    download only as fallback when stream URLs fail.
    """
    # Try 1: Get direct stream URL FIRST (fastest — instant playback)
    LOG.info("Getting video stream URL for: %s", url)
    stream_url = await get_video_stream_url(url)
    if stream_url:
        LOG.info("Using video stream URL for: %s", url)
        return stream_url, True

    # Try 2: Download to disk (fallback)
    LOG.info("Video stream URL failed, downloading for: %s", url)
    filepath = await download_video(url)
    if filepath and os.path.isfile(filepath):
        return filepath, False

    # Try 3: Combined search+download (bypasses URL-specific issues)
    from MusicLyrics.plugins.play.platforms.youtube import get_video_info
    info = await get_video_info(url)
    title = info.get("title", "") if info else ""
    if title and title not in ("YouTube Video", "Unknown"):
        LOG.info("Video URL extraction failed, trying search+download with title: %s", title)
        filepath_sd, _ = await search_and_download_video(title)
        if filepath_sd and os.path.isfile(filepath_sd):
            return filepath_sd, False

    # Try 4: SoundCloud as LAST RESORT fallback
    if title and title not in ("YouTube Video", "Unknown"):
        LOG.info("All video methods failed, trying SoundCloud fallback for: %s", title)
        sc_path, sc_info = await search_and_download_soundcloud(title)
        if sc_path:
            if sc_info and sc_info.get("_is_stream_url"):
                return sc_path, True
            if os.path.isfile(sc_path):
                return sc_path, False

    return "", False


async def _resolve_video(query: str, platform: str):
    """Resolve query into (info_dict, media_path, is_stream_url) for video."""

    # YouTube URL
    if platform == "youtube":
        info = await get_video_info(query)
        if not info:
            info = {"title": "YouTube Video", "url": query,
                    "duration": 0, "thumbnail": "", "channel": ""}
        if info["duration"] > Config.DURATION_LIMIT_MIN * 60 and info["duration"] > 0:
            raise ValueError(
                f"ভিডিওটি {Config.DURATION_LIMIT_MIN} মিনিটের বেশি।"
            )
        media_path, is_stream = await _get_video_media(query)
        if not media_path:
            title_query = info.get("title", "")
            channel_query = info.get("channel", "")
            if title_query and title_query != "YouTube Video":
                LOG.info("YouTube video URL extraction failed, trying search+download: %s", title_query)
                filepath, dl_info = await search_and_download_video(
                    f"{title_query} {channel_query}".strip()
                )
                if filepath:
                    return (dl_info or info), filepath, False
            raise ValueError("YouTube থেকে video পাওয়া যায়নি।")
        return info, media_path, is_stream

    # Spotify — search YT for video
    if platform == "spotify":
        track = await get_spotify_track(query)
        if not track:
            raise ValueError("Spotify link parse করা যায়নি।")
        yt = await search_youtube(track["query"])
        if not yt:
            # Fallback: SoundCloud
            LOG.info("Spotify -> YouTube video search failed, trying SoundCloud for: %s", track["query"])
            sc_path, sc_info = await search_and_download_soundcloud(track["query"])
            if sc_path and sc_info:
                is_stream = bool(sc_info.get("_is_stream_url"))
                info = {
                    "title": sc_info.get("title", track.get("title", "Unknown")),
                    "url": sc_info.get("url", query),
                    "duration": sc_info.get("duration", 0),
                    "thumbnail": sc_info.get("thumbnail", ""),
                    "channel": sc_info.get("channel", track.get("artist", "")),
                    "platform": "soundcloud",
                }
                return info, sc_path, is_stream
            raise ValueError("YouTube ও SoundCloud কোথাও video পাওয়া যায়নি।")
        media_path, is_stream = await _get_video_media(yt["url"])
        if not media_path:
            # Fallback: SoundCloud
            LOG.info("Spotify -> YouTube video download failed, trying SoundCloud for: %s", track["query"])
            sc_path, sc_info = await search_and_download_soundcloud(track["query"])
            if sc_path and sc_info:
                is_stream = bool(sc_info.get("_is_stream_url"))
                info = {
                    "title": sc_info.get("title", track.get("title", "Unknown")),
                    "url": sc_info.get("url", query),
                    "duration": sc_info.get("duration", 0),
                    "thumbnail": sc_info.get("thumbnail", ""),
                    "channel": sc_info.get("channel", track.get("artist", "")),
                    "platform": "soundcloud",
                }
                return info, sc_path, is_stream
            raise ValueError("Video stream পাওয়া যায়নি।")
        return {**yt, "platform": "spotify"}, media_path, is_stream

    # Apple Music — search YT for video
    if platform == "apple_music":
        track = await get_apple_music_track(query)
        if not track:
            raise ValueError("Apple Music link parse করা যায়নি।")
        yt = await search_youtube(track["query"])
        if not yt:
            sc_path, sc_info = await search_and_download_soundcloud(track["query"])
            if sc_path and sc_info:
                is_stream = bool(sc_info.get("_is_stream_url"))
                info = {
                    "title": sc_info.get("title", track.get("title", "Unknown")),
                    "url": sc_info.get("url", query),
                    "duration": sc_info.get("duration", 0),
                    "thumbnail": sc_info.get("thumbnail", ""),
                    "channel": sc_info.get("channel", track.get("artist", "")),
                    "platform": "soundcloud",
                }
                return info, sc_path, is_stream
            raise ValueError("YouTube ও SoundCloud কোথাও video পাওয়া যায়নি।")
        media_path, is_stream = await _get_video_media(yt["url"])
        if not media_path:
            sc_path, sc_info = await search_and_download_soundcloud(track["query"])
            if sc_path and sc_info:
                is_stream = bool(sc_info.get("_is_stream_url"))
                info = {
                    "title": sc_info.get("title", track.get("title", "Unknown")),
                    "url": sc_info.get("url", query),
                    "duration": sc_info.get("duration", 0),
                    "thumbnail": sc_info.get("thumbnail", ""),
                    "channel": sc_info.get("channel", track.get("artist", "")),
                    "platform": "soundcloud",
                }
                return info, sc_path, is_stream
            raise ValueError("Video stream পাওয়া যায়নি।")
        return {**yt, "platform": "apple_music"}, media_path, is_stream

    # SoundCloud URL — video (will play audio from SoundCloud)
    if platform == "soundcloud":
        sc_info = await get_soundcloud_info(query)
        if not sc_info:
            sc_info = {"title": "SoundCloud Audio", "url": query,
                       "duration": 0, "thumbnail": "", "channel": "",
                       "platform": "soundcloud"}
        filepath = await download_soundcloud(query)
        if filepath and os.path.isfile(filepath):
            return sc_info, filepath, False
        stream_url = await get_soundcloud_stream_url(query)
        if stream_url:
            return sc_info, stream_url, True
        raise ValueError("SoundCloud থেকে audio/video পাওয়া যায়নি।")

    # JioSaavn — video not available, extract song info and search YT
    if platform == "jiosaavn":
        song = await get_jiosaavn_song(query)
        search_query = query
        if song:
            search_query = f"{song['title']} {song.get('artist', '')}".strip()
        yt = await search_youtube(search_query)
        if not yt:
            sc_path, sc_info = await search_and_download_soundcloud(search_query)
            if sc_path and sc_info:
                is_stream = bool(sc_info.get("_is_stream_url"))
                info = {
                    "title": sc_info.get("title", song.get("title", "Unknown") if song else "Unknown"),
                    "url": sc_info.get("url", query),
                    "duration": sc_info.get("duration", 0),
                    "thumbnail": sc_info.get("thumbnail", ""),
                    "channel": sc_info.get("channel", song.get("artist", "") if song else ""),
                    "platform": "soundcloud",
                }
                return info, sc_path, is_stream
            raise ValueError("JioSaavn video সমর্থন করে না এবং YouTube/SoundCloud-এও পাওয়া যায়নি।")
        media_path, is_stream = await _get_video_media(yt["url"])
        if not media_path:
            sc_path, sc_info = await search_and_download_soundcloud(search_query)
            if sc_path and sc_info:
                is_stream = bool(sc_info.get("_is_stream_url"))
                info = {
                    "title": sc_info.get("title", song.get("title", "Unknown") if song else "Unknown"),
                    "url": sc_info.get("url", query),
                    "duration": sc_info.get("duration", 0),
                    "thumbnail": sc_info.get("thumbnail", ""),
                    "channel": sc_info.get("channel", song.get("artist", "") if song else ""),
                    "platform": "soundcloud",
                }
                return info, sc_path, is_stream
            raise ValueError("Video stream পাওয়া যায়নি।")
        return yt, media_path, is_stream

    # Direct URL
    if platform == "direct_url":
        info = await get_video_info(query)
        if not info:
            info = {"title": "Direct Video", "url": query,
                    "duration": 0, "thumbnail": "", "channel": ""}
        media_path, is_stream = await _get_video_media(query)
        if not media_path:
            raise ValueError("URL থেকে video পাওয়া যায়নি।")
        return info, media_path, is_stream

    # Plain text query — Priority: JioSaavn → YouTube → SoundCloud
    # 1. JioSaavn (direct CDN, works reliably for Indian music)
    LOG.info("Video query: trying JioSaavn first for: %s", query)
    try:
        js_path, js_info = await search_and_download_jiosaavn(query)
        if js_path and js_info:
            import os as _os
            if _os.path.isfile(js_path):
                LOG.info("JioSaavn found for video query (audio only): %s", js_info.get("title"))
                info = {
                    "title": js_info.get("title", "Unknown"),
                    "url": js_info.get("url", ""),
                    "duration": js_info.get("duration", 0),
                    "thumbnail": js_info.get("thumbnail", ""),
                    "channel": js_info.get("artist", ""),
                    "platform": "jiosaavn",
                }
                return info, js_path, False
    except Exception:
        LOG.debug("JioSaavn search failed for video query: %s", query)

    # 2. YouTube search + video stream/download
    yt = await search_youtube(query)
    if yt:
        if yt["duration"] > Config.DURATION_LIMIT_MIN * 60 and yt["duration"] > 0:
            raise ValueError(
                f"ভিডিওটি {Config.DURATION_LIMIT_MIN} মিনিটের বেশি।"
            )
        media_path, is_stream = await _get_video_media(yt["url"])
        if media_path:
            return yt, media_path, is_stream

    # 3. YouTube yt-dlp combined search+download
    LOG.info("Video search failed, trying combined search+download for: %s", query)
    filepath, dl_info = await search_and_download_video(query)
    if filepath and dl_info:
        return dl_info, filepath, False

    # 4. SoundCloud LAST RESORT
    LOG.info("All YouTube video methods failed, trying SoundCloud for: %s", query)
    sc_path, sc_info = await search_and_download_soundcloud(query)
    if sc_path and sc_info:
        is_stream = bool(sc_info.get("_is_stream_url"))
        return sc_info, sc_path, is_stream
    raise ValueError("কোনো result পাওয়া যায়নি।")


@bot.on_message(filters.command(["vplay", "vp"]) & not_edited)
async def vplay_command(client: Client, message: Message):
    """Handle /vplay <query|url> — video streaming."""
    chat_id = message.chat.id
    user = message.from_user
    requester = user.mention if user else "Unknown"
    requester_id = user.id if user else 0

    query = ""
    if len(message.command) > 1:
        query = " ".join(message.command[1:])
    elif message.reply_to_message and message.reply_to_message.text:
        query = message.reply_to_message.text

    if not query:
        usage_msg = await message.reply_text(
            "**Usage:** `/vplay <song name or URL>`\n\n"
            "Video সহ voice chat-এ stream করবে।\n\n"
            "Example: `/vplay Arijit Singh live`"
        )
        await _add_reaction(chat_id, usage_msg.id)
        return

    status_msg = await message.reply_text(
        f"🎬 **Video খুঁজছি:** `{query[:80]}`\n\nঅপেক্ষা করুন..."
    )
    await _add_reaction(chat_id, status_msg.id)

    platform = _detect_platform(query)

    try:
        # Pre-join VC concurrently while resolving media (speed optimization)
        pre_join_task = asyncio.create_task(pre_join_vc(chat_id))
        try:
            info, media_path, is_stream = await _resolve_video(query, platform)
        finally:
            try:
                await pre_join_task
            except Exception:
                pass
    except ValueError as exc:
        await status_msg.edit_text(f"❌ **Error:** {exc}")
        return
    except Exception as exc:
        LOG.exception("Unexpected error in /vplay for %s", chat_id)
        await status_msg.edit_text(
            f"❌ কিছু একটা সমস্যা হয়েছে। পরে আবার চেষ্টা করুন।\n"
            f"**Details:** `{type(exc).__name__}: {str(exc)[:200]}`"
        )
        return

    title = info.get("title", "Unknown")
    duration = info.get("duration", 0)
    thumbnail = info.get("thumbnail", "")
    url = info.get("url", query)
    channel = info.get("channel", "")

    item = QueueItem(
        title=title,
        url=url,
        media_path=media_path,
        duration=duration,
        requester=requester,
        requester_id=requester_id,
        thumbnail=thumbnail,
        stream_type="video",
        platform=platform if platform != "query" else "youtube",
        is_stream_url=is_stream,
    )

    position = await add_to_queue(chat_id, item)

    if position > 1 and is_active(chat_id):
        dur = format_duration(duration)
        color = _get_next_color()
        await status_msg.edit_text(
            f"**🎬 Queue-তে যোগ হয়েছে #{position}** (Video)\n\n"
            f"**Title:** {title}\n"
            f"**Duration:** {dur}\n"
            f"**Requested by:** {requester}",
            reply_markup=_control_keyboard(color),
        )
        await _add_reaction(chat_id, status_msg.id)
        return

    try:
        await stream_video(
            chat_id, media_path,
            title=title, duration=duration,
            thumbnail=thumbnail, requester=requester,
        )
    except FileNotFoundError:
        LOG.exception("Media not found for video stream in %s", chat_id)
        await status_msg.edit_text(
            "❌ ভিডিও ফাইল/URL পাওয়া যায়নি।\n"
            "আবার `/vplay` দিয়ে চেষ্টা করুন।"
        )
        return
    except RuntimeError as exc:
        await status_msg.edit_text(
            f"❌ {exc}\n\n"
            "STRING_SESSION সেট করা আছে কিনা চেক করুন।"
        )
        return
    except Exception as exc:
        LOG.exception("Video stream start failed in %s", chat_id)
        await status_msg.edit_text(
            "❌ Voice chat-এ video stream করা যাচ্ছে না।\n"
            "নিশ্চিত করুন voice chat চালু আছে এবং "
            "assistant গ্রুপে আছে।\n\n"
            f"**Error:** `{type(exc).__name__}: {str(exc)[:150]}`"
        )
        return

    # Start progress timer for the video track
    await _start_progress_timer(chat_id, duration)

    dur = format_duration(duration)
    color = _get_next_color()
    t = _get_current_theme()
    text = (
        f"{t['header']} **ᴘʟᴀʏʙᴀᴄᴋ ᴀᴄᴛɪᴠᴀᴛᴇᴅ | 🎬 ᴠɪᴅᴇᴏ**\n\n"
        f"> {t['title_icon']}  **ᴛɪᴛʟᴇ :** [{title}]({url})\n"
        f"> {t['dur_icon']}  **ᴅᴜʀᴀᴛɪᴏɴ :** {dur}\n"
        f"> 🎤  **ᴄʜᴀɴɴᴇʟ :** {channel}\n"
        f"> 👤  **ʀᴇǫᴜᴇꜱᴛᴇᴅ :** {requester}"
    )

    try:
        if thumbnail:
            await status_msg.delete()
            now_playing_msg = await bot.send_photo(
                chat_id,
                photo=thumbnail,
                caption=text,
                reply_markup=_control_keyboard(color),
            )
            # Track this message so we can delete it when track ends
            if chat_id not in _now_playing_messages:
                _now_playing_messages[chat_id] = []
            _now_playing_messages[chat_id].append(now_playing_msg)
            await _add_reaction(chat_id, now_playing_msg.id)
        else:
            await status_msg.edit_text(text, reply_markup=_control_keyboard(color))
            # Track this message
            if chat_id not in _now_playing_messages:
                _now_playing_messages[chat_id] = []
            _now_playing_messages[chat_id].append(status_msg)
            await _add_reaction(chat_id, status_msg.id)
    except Exception:
        await status_msg.edit_text(text, reply_markup=_control_keyboard(color))
        if chat_id not in _now_playing_messages:
            _now_playing_messages[chat_id] = []
        _now_playing_messages[chat_id].append(status_msg)
