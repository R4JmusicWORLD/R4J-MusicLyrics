from MusicLyrics.mongo.db import db

_col = db["sudo_users"]


async def add_sudo(user_id: int):
    """Add a user to the sudo list."""
    await _col.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True,
    )


async def remove_sudo(user_id: int):
    """Remove a user from the sudo list."""
    await _col.delete_one({"user_id": user_id})


async def get_sudos():
    """Return all sudo user documents."""
    return await _col.find().to_list(length=None)


async def is_sudo(user_id: int) -> bool:
    """Check whether a user is in the sudo list."""
    return await _col.find_one({"user_id": user_id}) is not None
