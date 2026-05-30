from pyrogram import Client
from pyrogram.enums import ParseMode
from config import Config

bot = Client(
    name="MusicLyricsBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    parse_mode=ParseMode.MARKDOWN,
)

# ── Cached bot info to avoid repeated get_me() API calls ────────────────────
# Calling client.get_me() on every message triggers users.GetFullUser
# on Telegram's API, causing FloodWait warnings. We cache the result
# after the first call and reuse it everywhere.
_bot_info_cache = None


async def get_bot_info():
    """Return cached bot info (User object). Calls get_me() only once."""
    global _bot_info_cache
    if _bot_info_cache is None:
        _bot_info_cache = await bot.get_me()
    return _bot_info_cache


def get_bot_info_sync():
    """Return cached bot info if available (non-async, returns None if not cached yet)."""
    return _bot_info_cache
