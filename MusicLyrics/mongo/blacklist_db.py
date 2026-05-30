from MusicLyrics.mongo.db import db

_col = db["blacklist"]


async def add_blacklist(chat_id: int, word: str):
    """Add a word to the chat's blacklist."""
    await _col.update_one(
        {"chat_id": chat_id, "word": word.lower()},
        {"$set": {"chat_id": chat_id, "word": word.lower()}},
        upsert=True,
    )


async def get_blacklist(chat_id: int):
    """Return all blacklisted words for a chat."""
    return await _col.find({"chat_id": chat_id}).to_list(length=None)


async def delete_blacklist(chat_id: int, word: str):
    """Remove a word from the chat's blacklist."""
    await _col.delete_one({"chat_id": chat_id, "word": word.lower()})


async def count_blacklist(chat_id: int) -> int:
    """Return the number of blacklisted words in a chat."""
    return await _col.count_documents({"chat_id": chat_id})
