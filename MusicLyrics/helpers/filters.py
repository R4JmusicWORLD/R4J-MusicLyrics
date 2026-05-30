"""Custom Pyrogram filters for MusicLyrics bot."""

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatType

from config import Config


async def _sudo_check(_, __, message: Message) -> bool:
    """Check if user is in SUDO_USERS or is OWNER_ID."""
    if not message.from_user:
        return False
    uid = message.from_user.id
    return uid == Config.OWNER_ID or uid in Config.SUDO_USERS


async def _admin_check(_, client, message: Message) -> bool:
    """Check if user is an admin in the current chat."""
    if not message.from_user:
        return False
    if message.chat.type == ChatType.PRIVATE:
        return True
    uid = message.from_user.id
    if uid == Config.OWNER_ID or uid in Config.SUDO_USERS:
        return True
    try:
        from pyrogram.enums import ChatMemberStatus

        member = await client.get_chat_member(message.chat.id, uid)
        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except Exception:
        return False


async def _owner_check(_, __, message: Message) -> bool:
    """Check if user is the bot owner."""
    if not message.from_user:
        return False
    return message.from_user.id == Config.OWNER_ID


async def _group_check(_, __, message: Message) -> bool:
    """Check if the chat is a group or supergroup."""
    return message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)


async def _private_check(_, __, message: Message) -> bool:
    """Check if the chat is a private chat."""
    return message.chat.type == ChatType.PRIVATE


async def _not_edited_check(_, __, message: Message) -> bool:
    """Return True if the message is NOT an edited message."""
    return not getattr(message, "edit_date", None)


sudo_filter = filters.create(_sudo_check, name="SudoFilter")
admin_filter = filters.create(_admin_check, name="AdminFilter")
owner_filter = filters.create(_owner_check, name="OwnerFilter")
group_filter = filters.create(_group_check, name="GroupFilter")
private_filter = filters.create(_private_check, name="PrivateFilter")
not_edited = filters.create(_not_edited_check, name="NotEditedFilter")
