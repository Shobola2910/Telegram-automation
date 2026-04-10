"""
Telegram client via Telethon — sends messages FROM the user's own account.
Not a bot. Uses MTProto directly.
"""
import logging
import asyncio
from typing import Optional
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, ChatFull, User
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

logger = logging.getLogger(__name__)

# Global singleton
_tg_client: Optional[TelegramClient] = None
_tg_ready = False


async def init_telegram(api_id: int, api_hash: str, session_string: str = "") -> TelegramClient:
    global _tg_client, _tg_ready
    session = StringSession(session_string) if session_string else StringSession()
    client = TelegramClient(session, api_id, api_hash)
    await client.connect()
    _tg_client = client
    _tg_ready = await client.is_user_authorized()
    return client


async def get_client() -> Optional[TelegramClient]:
    return _tg_client


async def is_authorized() -> bool:
    global _tg_ready
    if _tg_client is None:
        return False
    _tg_ready = await _tg_client.is_user_authorized()
    return _tg_ready


async def send_code_request(phone: str) -> str:
    """Send OTP code to phone — returns phone_code_hash"""
    if _tg_client is None:
        raise RuntimeError("Telegram client not initialized")
    result = await _tg_client.send_code_request(phone)
    return result.phone_code_hash


async def sign_in(phone: str, code: str, phone_code_hash: str,
                  password: str = "") -> dict:
    """Complete sign-in with OTP code"""
    if _tg_client is None:
        raise RuntimeError("Telegram client not initialized")
    try:
        await _tg_client.sign_in(phone, code, phone_code_hash=phone_code_hash)
    except Exception as e:
        if "password" in str(e).lower() and password:
            await _tg_client.sign_in(password=password)
        else:
            raise
    session_string = _tg_client.session.save()
    me = await _tg_client.get_me()
    return {
        "session_string": session_string,
        "user_id": me.id,
        "username": me.username,
        "first_name": me.first_name,
    }


async def get_session_string() -> str:
    if _tg_client is None:
        return ""
    return _tg_client.session.save()


async def send_message(chat_id: str, text: str) -> bool:
    """Send a message to a group/channel by chat_id"""
    if _tg_client is None or not await is_authorized():
        logger.error("Telegram not authorized")
        return False
    try:
        # chat_id can be numeric string or username
        target = int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id
        await _tg_client.send_message(target, text)
        logger.info(f"✅ Message sent to {chat_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send to {chat_id}: {e}")
        return False


async def get_all_groups() -> list[dict]:
    """Return all groups/channels the user is a member of"""
    if _tg_client is None or not await is_authorized():
        return []
    try:
        dialogs = await _tg_client.get_dialogs(limit=500)
        groups = []
        for dialog in dialogs:
            entity = dialog.entity
            if isinstance(entity, (Channel, Chat)):
                chat_type = "channel"
                if isinstance(entity, Chat):
                    chat_type = "group"
                elif hasattr(entity, "megagroup") and entity.megagroup:
                    chat_type = "supergroup"

                groups.append({
                    "chat_id": str(-entity.id) if isinstance(entity, Channel)
                               else str(-entity.id),
                    "title": dialog.title,
                    "chat_type": chat_type,
                    "member_count": getattr(entity, "participants_count", None),
                })
        return groups
    except Exception as e:
        logger.error(f"get_all_groups error: {e}")
        return []


async def disconnect():
    global _tg_client, _tg_ready
    if _tg_client:
        await _tg_client.disconnect()
    _tg_client = None
    _tg_ready = False
