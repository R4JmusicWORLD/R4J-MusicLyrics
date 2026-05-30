from MusicLyrics.mongo.db import db

_col = db["warns"]

_DEFAULT_WARN_LIMIT = 3


async def add_warn(chat_id: int, user_id: int, reason: str = ""):
    """Add a warning for a user in a chat. Returns the new warn count."""
    await _col.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$push": {"reasons": reason}, "$inc": {"count": 1}},
        upsert=True,
    )
    doc = await _col.find_one({"chat_id": chat_id, "user_id": user_id})
    return doc["count"] if doc else 1


async def get_warns(chat_id: int, user_id: int):
    """Return the warn document for a user in a chat (count + reasons)."""
    return await _col.find_one({"chat_id": chat_id, "user_id": user_id})


async def remove_warn(chat_id: int, user_id: int):
    """Remove the latest warning for a user. Returns remaining count."""
    doc = await _col.find_one({"chat_id": chat_id, "user_id": user_id})
    if not doc or doc.get("count", 0) <= 0:
        return 0
    await _col.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$pop": {"reasons": 1}, "$inc": {"count": -1}},
    )
    return max(doc["count"] - 1, 0)


async def reset_warns(chat_id: int, user_id: int):
    """Reset all warnings for a user in a chat."""
    await _col.delete_one({"chat_id": chat_id, "user_id": user_id})


async def get_warn_settings(chat_id: int) -> int:
    """Return the warn limit for a chat."""
    settings_col = db["warn_settings"]
    doc = await settings_col.find_one({"chat_id": chat_id})
    if doc:
        return doc.get("warn_limit", _DEFAULT_WARN_LIMIT)
    return _DEFAULT_WARN_LIMIT


async def set_warn_limit(chat_id: int, limit: int):
    """Set the warn limit for a chat."""
    settings_col = db["warn_settings"]
    await settings_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "warn_limit": limit}},
        upsert=True,
    )
