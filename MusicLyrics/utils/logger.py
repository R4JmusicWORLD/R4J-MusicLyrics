"""Logging setup for MusicLyrics bot."""

from __future__ import annotations

import logging
import os
import sys

from config import Config

_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, "musiclyrics.log")

# ANSI colour codes
_COLORS = {
    "DEBUG": "\033[36m",     # cyan
    "INFO": "\033[32m",      # green
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[1;31m",  # bold red
}
_RESET = "\033[0m"


class _ColoredFormatter(logging.Formatter):
    """Formatter that injects ANSI colours based on log level."""

    def __init__(self, fmt: str, datefmt: str | None = None):
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        color = _COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{_RESET}"
        return super().format(record)


_FMT = "%(asctime)s | %(levelname)-18s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# Console handler (coloured)
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_ColoredFormatter(_FMT, _DATEFMT))

# File handler (plain text)
_file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter(_FMT, _DATEFMT))

# Root configuration (done once on import)
logging.basicConfig(
    level=logging.INFO,
    handlers=[_console_handler, _file_handler],
)

# Silence noisy third-party loggers
for _name in ("pyrogram", "aiohttp", "httpx"):
    logging.getLogger(_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger pre-configured with console + file handlers.

    Usage::

        from MusicLyrics.utils.logger import get_logger
        log = get_logger(__name__)
        log.info("Bot started")
    """
    return logging.getLogger(name)
