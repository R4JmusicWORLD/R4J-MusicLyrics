import logging

from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

_LOG = logging.getLogger(__name__)

try:
    _client = AsyncIOMotorClient(
        Config.MONGO_URL,
        serverSelectionTimeoutMS=5000,   # 5s timeout instead of 30s default
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
    )
    db = _client["MusicLyricsDB"]
except Exception as e:
    _LOG.error("Failed to create MongoDB client: %s", e)
    _client = None
    db = None
