from MusicLyrics.mongo.db import db

_col = db["filters"]


async def add_filter(chat_id: int, keyword: str, response: str):
    """Add or update a keyword-response filter for a chat."""
    await _col.update_one(
        {"chat_id": chat_id, "keyword": keyword.lower()},
        {"$set": {"chat_id": chat_id, "keyword": keyword.lower(), "response": response}},
        upsert=True,
    )


async def get_filter(chat_id: int, keyword: str):
    """Return the filter document for a specific keyword in a chat."""
    return await _col.find_one({"chat_id": chat_id, "keyword": keyword.lower()})


async def get_all_filters(chat_id: int):
    """Return all filter documents for a chat."""
    return await _col.find({"chat_id": chat_id}).to_list(length=None)


async def delete_filter(chat_id: int, keyword: str):
    """Delete a filter by keyword in a chat."""
    await _col.delete_one({"chat_id": chat_id, "keyword": keyword.lower()})


async def count_filters(chat_id: int) -> int:
    """Return the number of filters in a chat."""
    return await _col.count_documents({"chat_id": chat_id})
