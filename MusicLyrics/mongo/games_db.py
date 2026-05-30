from datetime import datetime, timezone

from MusicLyrics.mongo.db import db

_col = db["game_scores"]


async def save_game_score(
    user_id: int, game: str, score: int, chat_id: int = 0
):
    """Record a game score entry."""
    await _col.insert_one(
        {
            "user_id": user_id,
            "game": game,
            "score": score,
            "chat_id": chat_id,
            "date": datetime.now(timezone.utc),
        }
    )


async def get_leaderboard(game: str, limit: int = 10):
    """Return the top scores for a game, sorted descending."""
    pipeline = [
        {"$match": {"game": game}},
        {
            "$group": {
                "_id": "$user_id",
                "best_score": {"$max": "$score"},
            }
        },
        {"$sort": {"best_score": -1}},
        {"$limit": limit},
    ]
    return await _col.aggregate(pipeline).to_list(length=limit)


async def get_user_stats(user_id: int, game: str | None = None):
    """Return all score documents for a user, optionally filtered by game."""
    query: dict = {"user_id": user_id}
    if game:
        query["game"] = game
    return await _col.find(query).to_list(length=None)
