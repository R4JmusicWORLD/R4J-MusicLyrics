# ─────────────────────────────────────────────────────────────────────────
# MusicLyrics — Copyright (c) 2026 R4J_81 (https://github.com/RajSukh81)
# Proprietary License — See LICENSE file for terms.
# Unauthorized copying, modification, or redistribution is prohibited.
# ─────────────────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration for MusicLyrics bot.

    All secrets and tunables are read from environment variables.
    See .env.example for the full list.
    """

    # ── Telegram API ─────────────────────────────────────────────────────
    try:
        API_ID = int(os.environ["API_ID"])
    except KeyError:
        raise SystemExit("ERROR: API_ID environment variable is required. Get it from https://my.telegram.org")
    API_HASH = os.environ.get("API_HASH")
    if not API_HASH:
        raise SystemExit("ERROR: API_HASH environment variable is required. Get it from https://my.telegram.org")
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    if not BOT_TOKEN:
        raise SystemExit("ERROR: BOT_TOKEN environment variable is required. Get it from @BotFather")
    STRING_SESSION = os.environ.get("STRING_SESSION", "")

    # ── Database ─────────────────────────────────────────────────────────
    MONGO_URL = os.environ.get(
        "MONGO_URL", "mongodb://localhost:27017/musiclyrics"
    )

    # ── Permissions ──────────────────────────────────────────────────────
    SUDO_USERS: list[int] = [
        int(uid)
        for uid in os.environ.get("SUDO_USERS", "").split()
        if uid.strip()
    ]
    _raw_owner = os.environ.get("OWNER_ID", "")
    if _raw_owner.strip():
        OWNER_ID: int = int(_raw_owner)
    elif SUDO_USERS:
        OWNER_ID: int = SUDO_USERS[0]
    else:
        OWNER_ID: int = 0

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_GROUP_ID = int(os.environ.get("LOG_GROUP_ID", 0))

    # ── Support & Branding ───────────────────────────────────────────────
    SUPPORT_GROUP = os.environ.get(
        "SUPPORT_GROUP", "https://t.me/+OvozYu7R1EczMGJl"
    )
    SUPPORT_CHANNEL = os.environ.get(
        "SUPPORT_CHANNEL", "https://t.me/RupkothaGolpo"
    )
    OWNER_LINK = "https://t.me/Raj_81"

    BOT_NAME = os.environ.get("BOT_USERNAME", "MusicLyrics")
    BRAND_PHOTO = (
        "https://pic-link-bot.lovable.app/i/"
        "telegram-1779340031479-5eab5504.jpg"
    )
    BRAND_PHOTO_2 = (
        "https://pic-link-bot.lovable.app/i/"
        "telegram-1779340095109-3b9afb55.jpg"
    )

    START_IMG = BRAND_PHOTO

    # ── Optional Integrations ────────────────────────────────────────────
    SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
    AI_API_KEY = os.environ.get("AI_API_KEY")
    COBALT_API_KEY = os.environ.get("COBALT_API_KEY", "")

    # ── Proxy for YouTube (essential for cloud deployments like Heroku) ──
    # Single proxy: supports multiple formats:
    #   - http://user:pass@host:port  (ready-to-use URL)
    #   - socks5://host:port          (SOCKS5 proxy)
    #   - ip:port:user:pass           (Webshare / common format, auto-converted)
    #   - user:pass@host:port         (auto-prefixed with http://)
    _YOUTUBE_PROXY_RAW = os.environ.get("YOUTUBE_PROXY", "").strip()

    @staticmethod
    def _parse_single_proxy(raw: str) -> str:
        """Parse a single proxy string into a valid http:// URL."""
        if not raw:
            return ""
        # Already a proper URL
        if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("socks"):
            return raw
        # Format: ip:port:user:pass (Webshare style)
        parts = raw.split(":")
        if len(parts) == 4:
            ip, port, user, pw = parts
            return f"http://{user}:{pw}@{ip}:{port}"
        # Format: user:pass@host:port (missing scheme)
        if "@" in raw:
            return f"http://{raw}"
        # Format: host:port (no auth)
        if len(parts) == 2:
            return f"http://{raw}"
        # Unknown — try with http prefix
        return f"http://{raw}"

    YOUTUBE_PROXY: str = _parse_single_proxy(_YOUTUBE_PROXY_RAW)

    # Multiple proxy rotation: set YOUTUBE_PROXY_LIST with proxies separated
    # by commas or newlines. Supported formats:
    #   - http://user:pass@host:port  (ready-to-use URL)
    #   - ip:port:user:pass           (Webshare / common format, auto-converted)
    #   - user:pass@host:port         (auto-prefixed with http://)
    YOUTUBE_PROXY_LIST_RAW = os.environ.get("YOUTUBE_PROXY_LIST", "")

    @staticmethod
    def _parse_proxy_list(raw: str) -> list[str]:
        """Parse proxy list from env var into list of http:// URLs."""
        if not raw.strip():
            return []
        proxies = []
        # Split by comma, newline, or semicolon
        for line in raw.replace(",", "\n").replace(";", "\n").split("\n"):
            line = line.strip()
            if not line:
                continue
            # Format: ip:port:user:pass (Webshare style)
            parts = line.split(":")
            if len(parts) == 4 and not line.startswith("http"):
                ip, port, user, pw = parts
                proxies.append(f"http://{user}:{pw}@{ip}:{port}")
            # Format: user:pass@host:port (missing scheme)
            elif "@" in line and not line.startswith("http"):
                proxies.append(f"http://{line}")
            # Format: already a URL
            elif line.startswith("http://") or line.startswith("https://") or line.startswith("socks"):
                proxies.append(line)
            else:
                # Unknown format, try as-is with http prefix
                proxies.append(f"http://{line}")
        return proxies

    YOUTUBE_PROXIES: list[str] = _parse_proxy_list(YOUTUBE_PROXY_LIST_RAW)

    # ── Playback Defaults ────────────────────────────────────────────────
    DURATION_LIMIT_MIN = int(os.environ.get("DURATION_LIMIT_MIN", 60))
    DOWNLOADS_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "downloads"
    )

    # ── Misc ─────────────────────────────────────────────────────────────
    PING_IMG = BRAND_PHOTO_2
    ALIVE_IMG = BRAND_PHOTO

    # ── Start message text ───────────────────────────────────────────────
    START_TEXT = (
        "**Hey {mention}! I'm {bot_name}** 🎵\n\n"
        "A powerful music streaming bot for Telegram voice chats.\n\n"
        "**Features:** Play music, lyrics lookup, games, security tools & more.\n\n"
        "Hit /help to see all commands.\n\n"
        f"[Support Group]({SUPPORT_GROUP}) | "
        f"[Updates Channel]({SUPPORT_CHANNEL}) | "
        f"[Owner]({OWNER_LINK})"
    )
