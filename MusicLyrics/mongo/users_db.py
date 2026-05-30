from MusicLyrics.mongo.db import db

_col = db["users"]


async def add_user(user_id: int, name: str = "", username: str = ""):
    """Insert or update a user document."""
    await _col.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "name": name, "username": username}},
        upsert=True,
    )


async def get_user(user_id: int):
    """Return a single user document or None."""
    return await _col.find_one({"user_id": user_id})


async def get_all_users():
    """Return a list of all user documents."""
    return await _col.find().to_list(length=None)


async def remove_user(user_id: int):
    """Delete a user document."""
    await _col.delete_one({"user_id": user_id})


async def count_users() -> int:
    """Return the total number of stored users."""
    return await _col.count_documents({})
