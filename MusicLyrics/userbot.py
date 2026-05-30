from pyrogram import Client
from pytgcalls import PyTgCalls
from config import Config

if Config.STRING_SESSION:
    userbot = Client(
        name="MusicLyricsUser",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        session_string=Config.STRING_SESSION,
    )
    pytgcalls = PyTgCalls(userbot)
else:
    userbot = None
    pytgcalls = None
