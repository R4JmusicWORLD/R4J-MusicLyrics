from MusicLyrics.mongo.db import db

_col = db["chats"]


async def add_chat(chat_id: int, title: str = ""):
    """Insert or update a chat document."""
    await _col.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "title": title}},
        upsert=True,
    )


async def get_chat(chat_id: int):
    """Return a single chat document or None."""
    return await _col.find_one({"chat_id": chat_id})


async def get_all_chats():
    """Return a list of all chat documents."""
    return await _col.find().to_list(length=None)


async def remove_chat(chat_id: int):
    """Delete a chat document."""
    await _col.delete_one({"chat_id": chat_id})


async def count_chats() -> int:
    """Return the total number of stored chats."""
    return await _col.count_documents({})


async def update_chat_settings(chat_id: int, settings: dict):
    """Merge *settings* into the chat document."""
    await _col.update_one(
        {"chat_id": chat_id},
        {"$set": settings},
        upsert=True,
    )
