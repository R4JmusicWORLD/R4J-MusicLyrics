from MusicLyrics.mongo.db import db

_col = db["notes"]


async def add_note(chat_id: int, name: str, content: str):
    """Add or update a note for a chat."""
    await _col.update_one(
        {"chat_id": chat_id, "name": name.lower()},
        {"$set": {"chat_id": chat_id, "name": name.lower(), "content": content}},
        upsert=True,
    )


async def get_note(chat_id: int, name: str):
    """Return a single note document or None."""
    return await _col.find_one({"chat_id": chat_id, "name": name.lower()})


async def get_all_notes(chat_id: int):
    """Return all note documents for a chat."""
    return await _col.find({"chat_id": chat_id}).to_list(length=None)


async def delete_note(chat_id: int, name: str):
    """Delete a note by name in a chat."""
    await _col.delete_one({"chat_id": chat_id, "name": name.lower()})
